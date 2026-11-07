# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields


class TestAccountAssetBarcodeAuditPro(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CompanyModel = cls.env['res.company']
        cls.company = cls.env.company

        # Accounts for Fixed Assets
        cls.account_asset = cls.env['account.account'].create({
            'name': 'Equipment & Machinery Test',
            'code': '180100',
            'account_type': 'asset_fixed',
            'company_ids': [(4, cls.company.id)],
        })
        cls.account_depreciation = cls.env['account.account'].create({
            'name': 'Accumulated Depreciation Equipment',
            'code': '180200',
            'account_type': 'asset_fixed',
            'company_ids': [(4, cls.company.id)],
        })
        cls.account_expense = cls.env['account.account'].create({
            'name': 'Depreciation Expense Test',
            'code': '681100',
            'account_type': 'expense',
            'company_ids': [(4, cls.company.id)],
        })
        cls.account_gain = cls.env['account.account'].create({
            'name': 'Gain on Disposal Test',
            'code': '750100',
            'account_type': 'income_other',
            'company_ids': [(4, cls.company.id)],
        })
        cls.account_loss = cls.env['account.account'].create({
            'name': 'Loss on Disposal Test',
            'code': '680100',
            'account_type': 'expense',
            'company_ids': [(4, cls.company.id)],
        })

        # General Journal for Depreciation
        cls.journal = cls.env['account.journal'].create({
            'name': 'Asset Operations Journal',
            'code': 'ASSET',
            'type': 'general',
            'company_id': cls.company.id,
        })

        # Asset Category
        cls.category = cls.env['account.asset.pro.category'].create({
            'name': 'Industrial Manufacturing Machinery',
            'method': 'straight_line',
            'method_number': 12,  # 12 periods
            'method_period': '1',  # monthly
            'journal_id': cls.journal.id,
            'account_asset_id': cls.account_asset.id,
            'account_depreciation_id': cls.account_depreciation.id,
            'account_expense_id': cls.account_expense.id,
            'account_gain_id': cls.account_gain.id,
            'account_loss_id': cls.account_loss.id,
            'company_id': cls.company.id,
        })

    def test_01_asset_creation_and_straight_line_computation(self):
        """Verify asset creation, sequence generation, and straight-line schedule calculation."""
        asset = self.env['account.asset.pro'].create({
            'name': 'CNC Precision Milling Station 5-Axis',
            'category_id': self.category.id,
            'original_value': 12000.0,
            'salvage_value': 0.0,
            'acquisition_date': fields.Date.today(),
            'first_depreciation_date': fields.Date.today(),
            'location_name': 'Plant Bay 1',
            'custodian_name': 'Frank Miller',
        })

        self.assertTrue(asset.code.startswith('AST/'))
        self.assertEqual(asset.depreciable_value, 12000.0)
        self.assertEqual(asset.value_residual, 12000.0)

        # Compute board
        asset.compute_depreciation_board()
        self.assertEqual(len(asset.depreciation_line_ids), 12)

        total_scheduled = sum(asset.depreciation_line_ids.mapped('amount'))
        self.assertEqual(round(total_scheduled, 2), 12000.0)
        self.assertEqual(asset.depreciation_line_ids[-1].remaining_value, 0.0)

        # Confirm asset
        asset.action_confirm()
        self.assertEqual(asset.state, 'open')

    def test_02_declining_balance_computation(self):
        """Verify declining balance (degressive) depreciation schedule."""
        asset = self.env['account.asset.pro'].create({
            'name': 'Enterprise High-Performance Server Cluster',
            'category_id': self.category.id,
            'method': 'degressive',
            'method_number': 5,
            'method_period': '12',  # Annual
            'method_progress_factor': 0.30,  # 30% declining
            'original_value': 10000.0,
            'salvage_value': 1000.0,
            'acquisition_date': fields.Date.today(),
            'first_depreciation_date': fields.Date.today(),
        })

        self.assertEqual(asset.depreciable_value, 9000.0)
        asset.compute_depreciation_board()
        self.assertEqual(len(asset.depreciation_line_ids), 5)

        total_scheduled = sum(asset.depreciation_line_ids.mapped('amount'))
        self.assertEqual(round(total_scheduled, 2), 9000.0)
        self.assertEqual(asset.depreciation_line_ids[-1].remaining_value, 1000.0)

    def test_03_journal_entry_posting(self):
        """Verify posting a depreciation line generates balanced account.move."""
        asset = self.env['account.asset.pro'].create({
            'name': 'Electric Forklift 3-Ton',
            'category_id': self.category.id,
            'original_value': 6000.0,
            'salvage_value': 0.0,
            'acquisition_date': fields.Date.today(),
            'first_depreciation_date': fields.Date.today(),
        })
        asset.compute_depreciation_board()
        asset.action_confirm()

        line1 = asset.depreciation_line_ids[0]
        self.assertFalse(line1.move_check)
        line1.action_post_line()

        self.assertTrue(line1.move_check)
        self.assertTrue(line1.move_id)
        self.assertEqual(line1.move_id.state, 'posted')
        self.assertEqual(asset.total_depreciated, line1.amount)
        self.assertEqual(asset.value_residual, 6000.0 - line1.amount)

    def test_04_barcode_audit_session_scanning(self):
        """Verify physical asset barcode audit session and scanning discrepancy detection."""
        asset_a = self.env['account.asset.pro'].create({
            'name': 'Laser Cutting Unit',
            'category_id': self.category.id,
            'original_value': 5000.0,
            'location_name': 'Facility Alpha',
            'barcode': 'BC-ASSET-001',
        })
        asset_a.action_confirm()

        asset_b = self.env['account.asset.pro'].create({
            'name': 'Hydraulic Press Machine',
            'category_id': self.category.id,
            'original_value': 8000.0,
            'location_name': 'Facility Beta',
            'barcode': 'BC-ASSET-002',
        })
        asset_b.action_confirm()

        # Audit session targeting Facility Alpha
        session = self.env['asset.audit.session'].create({
            'target_location': 'Facility Alpha',
            'audit_date': fields.Date.today(),
        })

        session.action_start_audit()
        self.assertEqual(session.state, 'in_progress')
        self.assertEqual(session.total_expected, 1)

        # Scan matching asset A
        session.barcode_scan_input = 'BC-ASSET-001'
        session.action_scan_barcode()
        self.assertEqual(session.total_verified, 1)

        # Scan asset B (which belongs to Facility Beta)
        session.barcode_scan_input = 'BC-ASSET-002'
        session.action_scan_barcode()
        self.assertEqual(session.total_discrepant, 1)

        # Scan unknown tag
        session.barcode_scan_input = 'TAG-UNKNOWN-999'
        session.action_scan_barcode()

        # Complete audit
        session.action_complete_audit()
        self.assertEqual(session.state, 'done')
        self.assertEqual(asset_a.audit_status, 'verified')

    def test_05_asset_disposal_wizard(self):
        """Verify asset disposal wizard writes off NBV and posts disposal move."""
        asset = self.env['account.asset.pro'].create({
            'name': 'Delivery Van Pro Master',
            'category_id': self.category.id,
            'original_value': 20000.0,
            'salvage_value': 0.0,
            'acquisition_date': fields.Date.today(),
            'first_depreciation_date': fields.Date.today(),
        })
        asset.compute_depreciation_board()
        asset.action_confirm()

        # Post 2 periods
        asset.depreciation_line_ids[0].action_post_line()
        asset.depreciation_line_ids[1].action_post_line()
        nbv_before = asset.value_residual

        # Launch disposal wizard for sale
        wizard = self.env['asset.disposal.wizard'].create({
            'asset_id': asset.id,
            'disposal_type': 'sale',
            'sale_amount': nbv_before + 1500.0,  # Gain of 1500
            'journal_id': self.journal.id,
        })
        wizard.action_confirm_disposal()

        self.assertEqual(asset.state, 'disposed')
        self.assertTrue(asset.disposal_move_id)
        self.assertEqual(asset.disposal_move_id.state, 'posted')
        self.assertEqual(len(asset.depreciation_line_ids.filtered(lambda l: not l.move_check)), 0)
