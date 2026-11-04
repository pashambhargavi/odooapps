# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestPettyCashWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Find or create cash journal & asset account
        cls.cash_journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'cash'),
        ], limit=1)
        if cls.cash_journal and cls.cash_journal.default_account_id:
            cls.cash_account = cls.cash_journal.default_account_id
        else:
            cls.cash_account = cls.env['account.account'].search([
                ('account_type', 'in', ('asset_current', 'asset_cash')),
            ], limit=1)
            if not cls.cash_account:
                cls.cash_account = cls.env['account.account'].create({
                    'name': 'Petty Cash Float Asset',
                    'code': '101099',
                    'account_type': 'asset_current',
                })
            if not cls.cash_journal:
                cls.cash_journal = cls.env['account.journal'].create({
                    'name': 'Petty Cash Journal',
                    'type': 'cash',
                    'code': 'PCJ',
                    'company_id': cls.company.id,
                    'default_account_id': cls.cash_account.id,
                })

        # Find bank journal
        cls.bank_journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('type', '=', 'bank'),
        ], limit=1)

        # Expense account
        cls.expense_account = cls.env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1)
        if not cls.expense_account:
            cls.expense_account = cls.env['account.account'].create({
                'name': 'General Office Expenses',
                'code': '601099',
                'account_type': 'expense',
            })

        # Fund Custodian
        cls.custodian = cls.env.user

        # Create Fund
        cls.fund = cls.env['petty.cash.fund'].create({
            'name': 'HQ Operations Petty Cash Float',
            'code': 'PC-HQ',
            'custodian_id': cls.custodian.id,
            'float_amount': 1000.0,
            'replenishment_threshold': 250.0,
            'account_id': cls.cash_account.id,
            'journal_id': cls.cash_journal.id,
            'company_id': cls.company.id,
        })
        cls.fund.action_activate()

    def test_01_fund_activation_and_limits(self):
        """Test petty cash fund initial state and capacity."""
        self.assertEqual(self.fund.state, 'active')
        self.assertEqual(self.fund.float_amount, 1000.0)
        self.assertEqual(self.fund.current_balance, 1000.0)
        self.assertEqual(self.fund.unreplenished_amount, 0.0)

    def test_02_voucher_lifecycle_and_accounting_posting(self):
        """Test full voucher lifecycle from draft to cash disbursement with GL entry."""
        voucher = self.env['petty.cash.voucher'].create({
            'fund_id': self.fund.id,
            'payee': 'Office Depot Stationery',
            'date': fields.Date.today(),
            'line_ids': [(0, 0, {
                'name': 'Printer Paper & Pens',
                'account_id': self.expense_account.id,
                'amount': 150.0,
            })],
        })
        self.assertEqual(voucher.amount_total, 150.0)
        self.assertEqual(voucher.state, 'draft')

        # Submit & Approve
        voucher.action_submit()
        self.assertEqual(voucher.state, 'submitted')
        voucher.action_approve()
        self.assertEqual(voucher.state, 'approved')

        # Disburse Cash (Pay)
        voucher.action_pay()
        self.assertEqual(voucher.state, 'paid')
        self.assertTrue(voucher.move_id, "Journal entry should be created.")
        self.assertEqual(voucher.move_id.state, 'posted')

        # Check Fund Balance update
        self.fund._compute_fund_balances()
        self.assertEqual(self.fund.unreplenished_amount, 150.0)
        self.assertEqual(self.fund.current_balance, 850.0)

    def test_03_insufficient_cash_prevention(self):
        """Test system blocks vouchers exceeding remaining cash balance."""
        excess_voucher = self.env['petty.cash.voucher'].create({
            'fund_id': self.fund.id,
            'payee': 'Luxury Catering',
            'line_ids': [(0, 0, {
                'name': 'Executive Banquet',
                'account_id': self.expense_account.id,
                'amount': 1500.0,  # Exceeds $1000 float
            })],
        })
        with self.assertRaises(UserError):
            excess_voucher.action_submit()

    def test_04_imprest_replenishment_cycle(self):
        """Test bank replenishment restoring float back to full capacity."""
        # Create paid voucher first
        voucher = self.env['petty.cash.voucher'].create({
            'fund_id': self.fund.id,
            'payee': 'Hardware Tools Co',
            'line_ids': [(0, 0, {
                'name': 'Emergency Maintenance Supplies',
                'account_id': self.expense_account.id,
                'amount': 200.0,
            })],
        })
        voucher.action_submit()
        voucher.action_approve()
        voucher.action_pay()

        # Create Replenishment
        replenishment = self.env['petty.cash.replenishment'].create({
            'fund_id': self.fund.id,
            'bank_journal_id': self.bank_journal.id,
            'voucher_ids': [(6, 0, [voucher.id])],
        })
        self.assertEqual(replenishment.total_reimbursement, 200.0)

        replenishment.action_submit()
        replenishment.action_approve()
        replenishment.action_reimburse()

        self.assertEqual(replenishment.state, 'reimbursed')
        self.assertEqual(voucher.state, 'replenished')
        self.assertTrue(replenishment.move_id)

    def test_05_physical_denomination_tally_and_report(self):
        """Test cash denomination counter and voucher PDF generation."""
        wizard = self.env['petty.cash.denomination.wizard'].create({
            'fund_id': self.fund.id,
            'system_balance': 1000.0,
            'count_100': 10,  # 10 x $100 = $1,000
        })
        wizard._compute_totals()
        self.assertEqual(wizard.counted_total, 1000.0)
        self.assertEqual(wizard.discrepancy, 0.0)
        self.assertEqual(wizard.discrepancy_status, 'match')

        res = wizard.action_confirm_tally()
        tally = self.env['petty.cash.tally'].browse(res['res_id'])
        self.assertEqual(tally.discrepancy_status, 'match')
        tally.action_approve()
        self.assertEqual(tally.state, 'approved')

        # Test PDF Report Rendering
        voucher = self.env['petty.cash.voucher'].search([('fund_id', '=', self.fund.id)], limit=1)
        if voucher:
            report = self.env.ref('petty_cash_expense_fund_manager.action_report_petty_cash_voucher')
            pdf, _ = report._render_qweb_pdf(report.id, [voucher.id])
            self.assertTrue(len(pdf) > 1000, "Voucher PDF slip should render successfully.")
