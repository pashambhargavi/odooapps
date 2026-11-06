# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestStockLandedCostsHub(TransactionCase):

    def setUp(self):
        super(TestStockLandedCostsHub, self).setUp()
        self.company = self.env.company
        self.LandedCostModel = self.env['stock.landed.cost.hub']
        self.ProductModel = self.env['product.product']
        self.PickingModel = self.env['stock.picking']
        self.StockMoveModel = self.env['stock.move']

        # Create two storable products
        self.product_a = self.ProductModel.create({
            'name': 'Industrial Servo Motor 500W',
            'type': 'consu', # or product
            'standard_price': 100.0,
            'weight': 5.0, # 5 kg
            'volume': 0.02,
        })
        self.product_b = self.ProductModel.create({
            'name': 'Titanium Flange Fitting 2-Inch',
            'type': 'consu',
            'standard_price': 300.0,
            'weight': 15.0, # 15 kg
            'volume': 0.05,
        })

        # Create Landed Cost service product
        self.cost_service = self.ProductModel.create({
            'name': 'Freight & Import Duty Service',
            'type': 'service',
            'default_code': 'SRV-TEST-FREIGHT',
        })

        # Find or create a receipt picking
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'),
            ('company_id', '=', self.company.id)
        ], limit=1)

        customer_loc = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
        stock_loc = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', self.company.id)], limit=1)

        self.picking = self.PickingModel.create({
            'picking_type_id': picking_type.id if picking_type else False,
            'location_id': customer_loc.id if customer_loc else 1,
            'location_dest_id': stock_loc.id if stock_loc else 1,
            'state': 'done',
        })

        # Create two stock moves
        self.move_a = self.StockMoveModel.create({
            'product_id': self.product_a.id,
            'product_uom_qty': 10.0,
            'quantity': 10.0,
            'product_uom': self.product_a.uom_id.id,
            'location_id': self.picking.location_id.id,
            'location_dest_id': self.picking.location_dest_id.id,
            'picking_id': self.picking.id,
            'state': 'done',
        })
        self.move_b = self.StockMoveModel.create({
            'product_id': self.product_b.id,
            'product_uom_qty': 10.0,
            'quantity': 10.0,
            'product_uom': self.product_b.uom_id.id,
            'location_id': self.picking.location_id.id,
            'location_dest_id': self.picking.location_dest_id.id,
            'picking_id': self.picking.id,
            'state': 'done',
        })

    def test_01_landed_cost_creation_and_sequence(self):
        """Test creating a landed cost document generates an auto-sequence."""
        lc = self.LandedCostModel.create({
            'date': '2026-11-06',
            'company_id': self.company.id,
        })
        self.assertTrue(lc.name.startswith('LC/'), "Reference should start with LC/ sequence prefix.")
        self.assertEqual(lc.state, 'draft', "Initial state must be draft.")
        self.assertEqual(lc.total_cost, 0.0, "Total cost should initially be 0.")

    def test_02_allocation_by_value(self):
        """Test landed cost allocation proportional to product cost/value."""
        # Product A value: 10 units * $100 = $1,000 (25% of total value)
        # Product B value: 10 units * $300 = $3,000 (75% of total value)
        # Total value = $4,000. Total freight = $400.
        # Product A should receive $100 freight, Product B should receive $300 freight.
        lc = self.LandedCostModel.create({
            'date': '2026-11-06',
            'company_id': self.company.id,
            'picking_ids': [(4, self.picking.id)],
            'cost_line_ids': [(0, 0, {
                'product_id': self.cost_service.id,
                'split_method': 'by_current_cost_price',
                'price_unit': 400.0,
            })]
        })

        lc.action_compute_landed_cost()
        self.assertEqual(lc.state, 'computed')
        self.assertEqual(len(lc.valuation_adjustment_lines), 2)

        val_a = lc.valuation_adjustment_lines.filtered(lambda v: v.product_id == self.product_a)
        val_b = lc.valuation_adjustment_lines.filtered(lambda v: v.product_id == self.product_b)

        self.assertAlmostEqual(val_a.additional_landed_cost, 100.0, places=2)
        self.assertAlmostEqual(val_b.additional_landed_cost, 300.0, places=2)

    def test_03_allocation_by_weight(self):
        """Test landed cost allocation proportional to gross weight."""
        # Product A total weight: 10 * 5kg = 50 kg (25% of 200 kg)
        # Product B total weight: 10 * 15kg = 150 kg (75% of 200 kg)
        # Freight = $800
        # Product A should get $200, Product B should get $600
        lc = self.LandedCostModel.create({
            'date': '2026-11-06',
            'company_id': self.company.id,
            'picking_ids': [(4, self.picking.id)],
            'cost_line_ids': [(0, 0, {
                'product_id': self.cost_service.id,
                'split_method': 'by_weight',
                'price_unit': 800.0,
            })]
        })

        lc.action_compute_landed_cost()
        val_a = lc.valuation_adjustment_lines.filtered(lambda v: v.product_id == self.product_a)
        val_b = lc.valuation_adjustment_lines.filtered(lambda v: v.product_id == self.product_b)

        self.assertAlmostEqual(val_a.additional_landed_cost, 200.0, places=2)
        self.assertAlmostEqual(val_b.additional_landed_cost, 600.0, places=2)

    def test_04_multi_currency_conversion(self):
        """Test foreign currency conversion on a landed cost charge line."""
        usd_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
        if not usd_currency:
            usd_currency = self.company.currency_id

        lc = self.LandedCostModel.create({
            'date': '2026-11-06',
            'company_id': self.company.id,
            'picking_ids': [(4, self.picking.id)],
            'cost_line_ids': [(0, 0, {
                'product_id': self.cost_service.id,
                'split_method': 'equal',
                'foreign_currency_id': usd_currency.id,
                'foreign_amount': 1000.0,
                'exchange_rate': 0.92, # $1,000 USD * 0.92 = 920.00 EUR
                'price_unit': 920.0,
            })]
        })

        self.assertEqual(lc.total_cost, 920.0, "Total cost should equal converted currency unit price.")

    def test_05_posting_and_product_revaluation(self):
        """Test posting landed cost updates product standard_price."""
        orig_price_a = self.product_a.standard_price
        orig_price_b = self.product_b.standard_price

        lc = self.LandedCostModel.create({
            'date': '2026-11-06',
            'company_id': self.company.id,
            'picking_ids': [(4, self.picking.id)],
            'cost_line_ids': [(0, 0, {
                'product_id': self.cost_service.id,
                'split_method': 'by_quantity',
                'price_unit': 200.0, # 20 units total -> $10 added cost per unit
            })]
        })

        lc.action_compute_landed_cost()
        lc.action_post_landed_cost()

        self.assertEqual(lc.state, 'posted', "State should be posted.")
        self.product_a.invalidate_recordset()
        self.product_b.invalidate_recordset()

        self.assertAlmostEqual(self.product_a.standard_price, orig_price_a + 10.0, places=2)
        self.assertAlmostEqual(self.product_b.standard_price, orig_price_b + 10.0, places=2)
