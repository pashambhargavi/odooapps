# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestConsignmentLifecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Partner: Vendor
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Consignment Partner Supplies LLC',
            'supplier_rank': 1,
            'is_company': True,
        })

        # Partner: Customer
        cls.customer = cls.env['res.partner'].create({
            'name': 'Premier Retail Store Ltd',
            'customer_rank': 1,
            'is_company': True,
        })

        # Product
        cls.product_a = cls.env['product.product'].create({
            'name': 'Consigned Medical Sensor',
            'type': 'consu',
            'list_price': 120.0,
            'standard_price': 80.0,
        })

        # Location
        parent_loc = cls.env.ref('stock.stock_location_stock', raise_if_not_found=False)
        if not parent_loc:
            parent_loc = cls.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

        cls.consignment_loc = cls.env['stock.location'].create({
            'name': 'Vendor Consignment Shelf A',
            'usage': 'internal',
            'location_id': parent_loc.id if parent_loc else False,
            'company_id': cls.company.id,
        })

        # Vendor Agreement
        cls.agreement = cls.env['consignment.agreement'].create({
            'partner_id': cls.vendor.id,
            'consignment_type': 'vendor',
            'location_id': cls.consignment_loc.id,
            'company_id': cls.company.id,
            'line_ids': [
                (0, 0, {
                    'product_id': cls.product_a.id,
                    'unit_price': 85.0,
                    'commission_rate': 10.0,
                    'max_stock_limit': 500.0,
                })
            ]
        })

    def test_01_agreement_activation(self):
        """Verify activation and validation constraints."""
        self.assertEqual(self.agreement.state, 'draft')
        self.agreement.action_activate()
        self.assertEqual(self.agreement.state, 'active')

        # Suspended and closed states
        self.agreement.action_suspend()
        self.assertEqual(self.agreement.state, 'suspended')
        self.agreement.action_close()
        self.assertEqual(self.agreement.state, 'closed')
        self.agreement.action_reset_draft()
        self.assertEqual(self.agreement.state, 'draft')

    def test_02_vendor_settlement_and_bill_generation(self):
        """Verify vendor settlement creation and auto vendor bill generation."""
        self.agreement.action_activate()

        settlement = self.env['consignment.settlement'].create({
            'agreement_id': self.agreement.id,
            'company_id': self.company.id,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'consumed_qty': 10.0,
                    'unit_price': 85.0,
                    'commission_rate': 10.0,
                })
            ]
        })

        self.assertEqual(settlement.total_consumed_qty, 10.0)
        self.assertEqual(settlement.total_settlement_amount, 850.0)
        self.assertEqual(settlement.total_commission_amount, 85.0)
        self.assertEqual(settlement.net_settlement_amount, 765.0)

        # Confirm settlement
        settlement.action_confirm()
        self.assertEqual(settlement.state, 'confirmed')

        # Generate Vendor Bill
        settlement.action_generate_invoice()
        self.assertEqual(settlement.state, 'invoiced')
        self.assertTrue(bool(settlement.invoice_id))
        self.assertEqual(settlement.invoice_id.move_type, 'in_invoice')
        self.assertEqual(settlement.invoice_id.partner_id, self.vendor)

    def test_03_customer_settlement_and_invoice_generation(self):
        """Verify customer consignment settlement creates an out_invoice."""
        cust_agr = self.env['consignment.agreement'].create({
            'partner_id': self.customer.id,
            'consignment_type': 'customer',
            'location_id': self.consignment_loc.id,
            'company_id': self.company.id,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'unit_price': 120.0,
                    'commission_rate': 5.0,
                })
            ]
        })
        cust_agr.action_activate()

        settlement = self.env['consignment.settlement'].create({
            'agreement_id': cust_agr.id,
            'company_id': self.company.id,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'consumed_qty': 5.0,
                    'unit_price': 120.0,
                    'commission_rate': 5.0,
                })
            ]
        })
        settlement.action_confirm()
        settlement.action_generate_invoice()

        self.assertEqual(settlement.state, 'invoiced')
        self.assertEqual(settlement.invoice_id.move_type, 'out_invoice')
        self.assertEqual(settlement.invoice_id.partner_id, self.customer)

    def test_04_consignment_stock_audit(self):
        """Verify physical count session and variance calculation."""
        self.agreement.action_activate()

        audit = self.env['consignment.audit'].create({
            'agreement_id': self.agreement.id,
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_a.id,
                    'theoretical_qty': 50.0,
                    'physical_qty': 48.0,
                    'unit_price': 85.0,
                })
            ]
        })

        self.assertEqual(audit.total_theoretical_qty, 50.0)
        self.assertEqual(audit.total_physical_qty, 48.0)
        self.assertEqual(audit.total_variance_qty, -2.0)
        self.assertEqual(audit.total_variance_value, -170.0)

        audit.action_reconcile()
        self.assertEqual(audit.state, 'reconciled')

    def test_05_partner_integration(self):
        """Verify partner smart button and agreement count."""
        self.agreement.action_activate()
        self.vendor._compute_consignment_stats()
        self.assertGreaterEqual(self.vendor.consignment_agreement_count, 1)
