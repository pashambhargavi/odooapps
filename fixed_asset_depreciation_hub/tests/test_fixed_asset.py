# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestFixedAsset(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Account = cls.env['account.account']
        cls.acc_asset = Account.create({'name': 'Test Equipment', 'code': 'FA100', 'account_type': 'asset_fixed'})
        cls.acc_accum = Account.create({'name': 'Test Accum. Depr.', 'code': 'FA101', 'account_type': 'asset_fixed'})
        cls.acc_expense = Account.create({
            'name': 'Test Depr. Expense', 'code': 'FA600', 'account_type': 'expense_depreciation'})
        cls.acc_loss = Account.create({'name': 'Test Disposal Loss', 'code': 'FA690', 'account_type': 'expense'})
        cls.category = cls.env['fixed.asset.category'].create({
            'name': 'Computers',
            'journal_id': cls.company_data['default_journal_misc'].id,
            'account_asset_id': cls.acc_asset.id,
            'account_depreciation_id': cls.acc_accum.id,
            'account_expense_id': cls.acc_expense.id,
            'account_loss_id': cls.acc_loss.id,
            'method': 'linear',
            'method_number': 12,
            'method_period': '1',
        })

    def _create_asset(self, **vals):
        values = {
            'name': 'Laptop',
            'category_id': self.category.id,
            'acquisition_date': date(2025, 1, 1),
            'original_value': 1200.0,
        }
        values.update(vals)
        return self.env['fixed.asset'].create(values)

    def test_01_linear_board(self):
        asset = self._create_asset(salvage_value=200.0)
        asset.action_confirm()
        self.assertEqual(asset.state, 'running')
        self.assertEqual(len(asset.line_ids), 12)
        self.assertAlmostEqual(sum(asset.line_ids.mapped('amount')), 1000.0)
        self.assertEqual(asset.line_ids[0].date, date(2025, 1, 31))
        self.assertEqual(asset.line_ids[1].date, date(2025, 2, 28))
        self.assertEqual(asset.line_ids[-1].date, date(2025, 12, 31))
        self.assertAlmostEqual(asset.line_ids[-1].remaining_value, 0.0)

    def test_02_linear_rounding_remainder(self):
        asset = self._create_asset(original_value=1000.0, method_number=3)
        asset.action_compute_board()
        self.assertEqual(asset.line_ids.mapped('amount'), [333.33, 333.33, 333.34])

    def test_03_prorata_adds_period(self):
        asset = self._create_asset(acquisition_date=date(2025, 1, 16), prorata=True)
        asset.action_compute_board()
        self.assertEqual(len(asset.line_ids), 13)
        # 16 of 31 days in January
        self.assertAlmostEqual(asset.line_ids[0].amount, round(100.0 * 16 / 31, 2))
        self.assertAlmostEqual(sum(asset.line_ids.mapped('amount')), 1200.0)

    def test_04_degressive_board(self):
        asset = self._create_asset(method='degressive', degressive_factor=2.0, method_number=5,
                                   method_period='12', original_value=10000.0)
        asset.action_compute_board()
        amounts = asset.line_ids.mapped('amount')
        self.assertEqual(amounts[0], 4000.0)   # 10000 * 2/5
        self.assertEqual(amounts[1], 2400.0)   # 6000 * 2/5
        self.assertAlmostEqual(sum(amounts), 10000.0)
        self.assertTrue(all(a > 0 for a in amounts))

    def test_05_post_line_creates_balanced_entry(self):
        asset = self._create_asset()
        asset.action_confirm()
        line = asset.line_ids[0]
        line.action_post()
        move = line.move_id
        self.assertEqual(move.state, 'posted')
        self.assertEqual(move.fixed_asset_id, asset)
        debit = move.line_ids.filtered(lambda l: l.account_id == self.acc_expense)
        credit = move.line_ids.filtered(lambda l: l.account_id == self.acc_accum)
        self.assertAlmostEqual(debit.debit, 100.0)
        self.assertAlmostEqual(credit.credit, 100.0)
        self.assertAlmostEqual(asset.depreciated_value, 100.0)
        self.assertAlmostEqual(asset.book_value, 1100.0)
        with self.assertRaises(UserError):
            asset.line_ids[3].action_post()   # earlier lines still unposted

    def test_06_cron_posts_due_lines_and_closes(self):
        asset = self._create_asset(acquisition_date=date(2020, 1, 1))
        asset.action_confirm()
        self.env['fixed.asset']._cron_post_depreciation()
        self.assertTrue(all(asset.line_ids.mapped('move_posted')))
        self.assertEqual(asset.state, 'close')
        self.assertAlmostEqual(asset.book_value, 0.0)

    def test_07_cron_skips_future_lines(self):
        today = fields.Date.today()
        asset = self._create_asset(acquisition_date=today.replace(day=1))
        asset.action_confirm()
        self.env['fixed.asset']._cron_post_depreciation()
        self.assertFalse(asset.line_ids.filtered(lambda l: l.date > today and l.move_id))

    def test_08_disposal(self):
        asset = self._create_asset()
        asset.action_confirm()
        asset.line_ids[:3].action_post()
        wizard = self.env['fixed.asset.dispose.wizard'].create({
            'asset_id': asset.id, 'disposal_date': date(2025, 4, 15)})
        wizard.action_dispose()
        self.assertEqual(asset.state, 'disposed')
        self.assertEqual(len(asset.line_ids), 3)
        move = asset.disposal_move_id
        self.assertEqual(move.state, 'posted')
        by_account = {l.account_id: l.balance for l in move.line_ids}
        self.assertAlmostEqual(by_account[self.acc_asset], -1200.0)
        self.assertAlmostEqual(by_account[self.acc_accum], 300.0)
        self.assertAlmostEqual(by_account[self.acc_loss], 900.0)

    def test_09_vendor_bill_creates_asset(self):
        self.category.auto_confirm = True
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': date(2025, 3, 10),
            'invoice_line_ids': [Command.create({
                'name': 'Server Rack',
                'quantity': 1,
                'price_unit': 2400.0,
                'account_id': self.acc_asset.id,
                'asset_category_id': self.category.id,
                'tax_ids': [Command.clear()],
            })],
        })
        bill.action_post()
        self.assertEqual(bill.created_asset_count, 1)
        asset = self.env['fixed.asset'].search([('source_move_line_id.move_id', '=', bill.id)])
        self.assertAlmostEqual(asset.original_value, 2400.0)
        self.assertEqual(asset.partner_id, self.partner_a)
        self.assertEqual(asset.state, 'running')
        self.assertEqual(len(asset.line_ids), 12)
        # Re-posting after reset must not duplicate the asset
        bill.button_draft()
        bill.action_post()
        self.assertEqual(bill.created_asset_count, 1)

    def test_10_guards(self):
        asset = self._create_asset()
        asset.action_confirm()
        asset.line_ids[0].action_post()
        with self.assertRaises(UserError):
            asset.action_compute_board()
        with self.assertRaises(UserError):
            asset.action_set_to_draft()
        with self.assertRaises(UserError):
            asset.unlink()
