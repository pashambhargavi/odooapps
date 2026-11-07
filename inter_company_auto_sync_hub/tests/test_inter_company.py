# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestInterCompanyAutoSyncHub(TransactionCase):

    def setUp(self):
        super(TestInterCompanyAutoSyncHub, self).setUp()
        self.CompanyModel = self.env['res.company']
        self.PartnerModel = self.env['res.partner']
        self.ProductModel = self.env['product.product']
        self.RuleModel = self.env['inter.company.rule']
        self.POModel = self.env['purchase.order']
        self.SOModel = self.env['sale.order']
        self.MoveModel = self.env['account.move']

        # Source Company A (Active company)
        self.company_a = self.env.company

        # Target Sister Company B
        self.company_b = self.CompanyModel.create({
            'name': 'Sister Entity Europe BV',
            'currency_id': self.env.ref('base.EUR').id if self.env.ref('base.EUR', raise_if_not_found=False) else self.company_a.currency_id.id,
        })

        # Create journals and accounts for Company B so invoices/bills can be created
        self.account_expense_b = self.env['account.account'].create({
            'name': 'Inter-Company Cost of Goods BV',
            'code': '510000B',
            'account_type': 'expense',
            'company_ids': [(4, self.company_b.id)],
        })
        self.account_payable_b = self.env['account.account'].create({
            'name': 'Inter-Company Payables BV',
            'code': '211000B',
            'account_type': 'liability_payable',
            'company_ids': [(4, self.company_b.id)],
        })
        self.journal_b_purchase = self.env['account.journal'].create({
            'name': 'Vendor Bills BV',
            'code': 'BILLB',
            'type': 'purchase',
            'company_id': self.company_b.id,
            'default_account_id': self.account_expense_b.id,
        })
        self.journal_b_sale = self.env['account.journal'].create({
            'name': 'Customer Invoices BV',
            'code': 'INVB',
            'type': 'sale',
            'company_id': self.company_b.id,
        })

        # Partner representing Company B inside Company A
        self.partner_b = self.PartnerModel.create({
            'name': 'Sister Entity Europe BV (Partner)',
            'company_id': self.company_a.id,
            'is_company': True,
        })

        # Partner representing Company A inside Company B
        self.partner_a = self.PartnerModel.create({
            'name': 'Primary Entity US (Partner)',
            'company_id': self.company_b.id,
            'is_company': True,
        })
        self.partner_a.with_company(self.company_b).property_account_payable_id = self.account_payable_b

        # Test Storable Product
        self.product = self.ProductModel.create({
            'name': 'Precision Hydraulic Valve V2',
            'type': 'consu',
            'standard_price': 100.0,
            'list_price': 150.0,
        })

        # Base Inter-Company Rule
        self.rule = self.RuleModel.create({
            'name': 'Company A to Company B Trade Rule',
            'company_id': self.company_a.id,
            'target_company_id': self.company_b.id,
            'partner_id': self.partner_b.id,
            'target_partner_id': self.partner_a.id,
            'sync_po_to_so': True,
            'auto_confirm_so': False,
            'sync_invoice_to_bill': True,
            'pricing_rule': 'original_price',
            'elimination_code': 'IC-TEST-01',
        })

    def test_01_rule_creation_and_constraints(self):
        """Verify rule creation and constraint preventing self-company rules."""
        self.assertTrue(self.rule.active)
        self.assertEqual(self.rule.company_id, self.company_a)
        self.assertEqual(self.rule.target_company_id, self.company_b)

        # Attempting to create a rule where source == target must raise ValidationError
        with self.assertRaises(ValidationError):
            self.RuleModel.create({
                'name': 'Invalid Self Rule',
                'company_id': self.company_a.id,
                'target_company_id': self.company_a.id,
                'partner_id': self.partner_b.id,
            })

    def test_02_po_to_so_mirroring(self):
        """Verify placing a PO in Company A auto-generates matching SO in Company B."""
        po = self.POModel.create({
            'partner_id': self.partner_b.id,
            'company_id': self.company_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 25.0,
                'product_uom_id': self.product.uom_id.id,
                'price_unit': 120.0,
                'name': 'Hydraulic Valve order',
                'date_planned': fields.Datetime.now(),
            })],
        })

        self.assertTrue(po.is_intercompany)
        po.button_confirm()

        # Mirrored SO must exist in Company B
        self.assertTrue(po.intercompany_sale_order_id)
        so = po.intercompany_sale_order_id
        self.assertEqual(so.company_id, self.company_b)
        self.assertEqual(so.partner_id, self.partner_a)
        self.assertEqual(so.auto_intercompany_created, True)
        self.assertEqual(so.client_order_ref, po.name)
        self.assertEqual(len(so.order_line), 1)
        self.assertEqual(so.order_line[0].product_id, self.product)
        self.assertEqual(so.order_line[0].product_uom_qty, 25.0)
        self.assertEqual(so.order_line[0].price_unit, 120.0)

    def test_03_transfer_pricing_cost_plus(self):
        """Verify transfer pricing engine with Cost-Plus Margin % markup."""
        self.rule.write({
            'pricing_rule': 'cost_plus_margin',
            'margin_percent': 25.0,  # 25% markup over standard cost ($100 * 1.25 = $125)
        })

        calculated_price = self.rule.calculate_transfer_price(self.product, base_price=100.0)
        self.assertEqual(calculated_price, 125.0)

        # Place PO and check resulting SO unit price
        po = self.POModel.create({
            'partner_id': self.partner_b.id,
            'company_id': self.company_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 10.0,
                'product_uom_id': self.product.uom_id.id,
                'price_unit': 100.0,
                'name': 'Valves',
                'date_planned': fields.Datetime.now(),
            })],
        })
        po.button_confirm()

        so = po.intercompany_sale_order_id
        self.assertTrue(so)
        self.assertEqual(so.order_line[0].price_unit, 125.0)

    def test_04_invoice_to_bill_mirroring(self):
        """Verify posting a Customer Invoice in Company A auto-creates matching Vendor Bill in Company B."""
        # Find sale journal in Company A
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_a.id)
        ], limit=1)

        invoice = self.MoveModel.create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b.id,
            'company_id': self.company_a.id,
            'journal_id': journal.id if journal else False,
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product.id,
                'quantity': 5.0,
                'price_unit': 200.0,
                'name': 'Consulting & Components',
            })],
        })

        self.assertTrue(invoice.is_intercompany)
        invoice.action_post()

        # Reciprocal Vendor Bill in Company B must exist
        self.assertTrue(invoice.intercompany_move_id)
        bill = invoice.intercompany_move_id
        self.assertEqual(bill.move_type, 'in_invoice')
        self.assertEqual(bill.company_id, self.company_b)
        self.assertEqual(bill.partner_id, self.partner_a)
        self.assertEqual(bill.ref, invoice.name)
        self.assertEqual(len(bill.invoice_line_ids), 1)
        self.assertEqual(bill.invoice_line_ids[0].quantity, 5.0)
        self.assertEqual(bill.invoice_line_ids[0].price_unit, 200.0)

    def test_05_execution_log_and_security(self):
        """Verify inter-company transaction audit log is logged upon sync."""
        po = self.POModel.create({
            'partner_id': self.partner_b.id,
            'company_id': self.company_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_qty': 2.0,
                'product_uom_id': self.product.uom_id.id,
                'price_unit': 50.0,
                'name': 'Valve',
                'date_planned': fields.Datetime.now(),
            })],
        })
        po.button_confirm()

        logs = self.env['inter.company.log'].sudo().search([
            ('rule_id', '=', self.rule.id),
            ('source_doc_ref', '=', po.name)
        ])
        self.assertTrue(logs)
        self.assertEqual(logs[0].state, 'success')
        self.assertEqual(logs[0].source_company_id, self.company_a)
        self.assertEqual(logs[0].target_company_id, self.company_b)
        self.assertEqual(logs[0].source_doc_type, 'purchase_order')
        self.assertEqual(logs[0].target_doc_type, 'sale_order')
