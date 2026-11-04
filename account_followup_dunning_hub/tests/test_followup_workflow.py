# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo import fields

class TestFollowupWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Apex Global Trading LLC',
            'email': 'apex.accounting@example.com',
            'customer_rank': 1,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Enterprise Consulting Services',
            'type': 'service',
            'list_price': 1500.0,
        })
        today = fields.Date.context_today(cls.partner)
        past_due = today - timedelta(days=20)
        cls.invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner.id,
            'invoice_date': past_due - timedelta(days=30),
            'invoice_date_due': past_due,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product.id,
                'quantity': 2,
                'price_unit': 1500.0,
            })],
        })
        cls.invoice.action_post()

    def test_01_followup_levels_setup(self):
        """Test default dunning levels exist and are ordered correctly."""
        levels = self.env['account.followup.level'].search([
            ('company_id', '=', self.company.id)
        ], order='delay asc')
        self.assertTrue(len(levels) >= 4, "Expected at least 4 default dunning levels.")
        delays = [l.delay for l in levels]
        self.assertEqual(delays, sorted(delays), "Levels should be ordered by delay ascending.")

    def test_02_invoice_overdue_calculation(self):
        """Test invoice overdue metrics and partner summary."""
        # Check invoice overdue metrics
        self.invoice._compute_overdue_metrics()
        self.assertTrue(self.invoice.is_overdue)
        self.assertEqual(self.invoice.days_overdue, 20)

        # Check partner metrics
        self.partner._compute_followup_metrics()
        self.assertTrue(self.partner.total_overdue_amount > 0)
        self.assertEqual(self.partner.max_days_overdue, 20)
        self.assertIn(self.partner.followup_status, ('with_overdue', 'in_need_of_action'))

    def test_03_manual_followup_wizard(self):
        """Test executing the manual customer follow-up workbench."""
        level = self.env['account.followup.level'].search([
            ('company_id', '=', self.company.id),
            ('delay', '<=', 20)
        ], order='delay desc', limit=1)

        wizard = self.env['account.followup.manual.wizard'].create({
            'partner_id': self.partner.id,
            'followup_level_id': level.id if level else False,
            'action_type': 'promise',
            'promised_payment_date': fields.Date.context_today(self.partner) + timedelta(days=5),
            'notes': 'Spoke with CFO Mr. Vance. Payment scheduled for Friday.',
        })
        wizard.action_confirm()

        # Check history audit record
        history = self.env['account.followup.history'].search([
            ('partner_id', '=', self.partner.id)
        ], limit=1)
        self.assertTrue(history, "History record should be created.")
        self.assertEqual(history.action_type, 'promise')
        self.assertIn('Vance', history.notes)

    def test_04_automated_cron_execution(self):
        """Test daily automated dunning cron job."""
        today = fields.Date.context_today(self.partner)
        self.partner.write({'next_followup_date': today})

        # Run cron
        self.env['res.partner']._cron_process_automated_followups()

        # Partner should have updated follow-up dates
        self.assertEqual(self.partner.latest_followup_date, today)
        self.assertTrue(self.partner.next_followup_date > today)

    def test_05_statement_of_account_report(self):
        """Test rendering the Statement of Account PDF report."""
        report = self.env.ref('account_followup_dunning_hub.action_report_statement_of_account')
        pdf_content, _ = report._render_qweb_pdf(report.id, [self.partner.id])
        self.assertTrue(len(pdf_content) > 1000, "PDF content should be generated and non-empty.")
