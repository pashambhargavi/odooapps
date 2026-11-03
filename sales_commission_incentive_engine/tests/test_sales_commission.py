# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.tests.common import TransactionCase


class TestSalesCommission(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sales_rep = cls.env['res.users'].create({
            'name': 'Test Sales Executive',
            'login': 'test_sales_rep_comm',
            'email': 'rep@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
                cls.env.ref('sales_commission_incentive_engine.group_commission_user').id,
            ])],
        })
        cls.sales_mgr = cls.env['res.users'].create({
            'name': 'Test Sales Manager Lead',
            'login': 'test_sales_mgr_comm',
            'email': 'mgr@example.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_manager').id,
                cls.env.ref('sales_commission_incentive_engine.group_commission_manager').id,
            ])],
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Global Trading Client Corp',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'High-End Laser Cutter',
            'type': 'consu',
            'list_price': 10000.0,
            'standard_price': 6000.0,
        })

    def test_01_flat_revenue_commission_on_so_confirmation(self):
        """Test flat 5% direct commission and 2% manager override on Sales Order confirmation."""
        plan = self.env['commission.plan'].create({
            'name': 'Test SO Confirmation Plan',
            'plan_type': 'flat',
            'calculation_basis': 'so_confirm',
            'flat_rate': 5.0,
            'enable_manager_override': True,
            'manager_override_rate': 2.0,
        })
        self.sales_rep.commission_plan_id = plan.id

        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'user_id': self.sales_rep.id,
            'sales_manager_id': self.sales_mgr.id,
            'commission_plan_id': plan.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'price_unit': 10000.0,
            })],
        })
        self.assertEqual(order.salesperson_commission_amount, 500.0)
        self.assertEqual(order.manager_commission_amount, 200.0)
        self.assertEqual(order.total_commission_amount, 700.0)

        # Confirm order -> creates commission ledger lines
        order.action_confirm()
        self.assertEqual(order.commission_line_count, 2)

        sp_line = order.commission_line_ids.filtered(lambda l: l.beneficiary_type == 'salesperson')
        mgr_line = order.commission_line_ids.filtered(lambda l: l.beneficiary_type == 'manager')

        self.assertEqual(sp_line.salesperson_id, self.sales_rep)
        self.assertEqual(sp_line.commission_amount, 500.0)
        self.assertEqual(mgr_line.salesperson_id, self.sales_mgr)
        self.assertEqual(mgr_line.commission_amount, 200.0)

    def test_02_margin_commission_plan(self):
        """Test gross profit margin-based commission calculation."""
        plan = self.env['commission.plan'].create({
            'name': 'Test 20% Margin Plan',
            'plan_type': 'margin',
            'calculation_basis': 'so_confirm',
            'margin_rate': 20.0,
            'enable_manager_override': False,
        })
        # Price = 10000, Cost = 6000 -> Gross Margin = 4000 -> 20% of 4000 = 800
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'user_id': self.sales_rep.id,
            'commission_plan_id': plan.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1.0,
                'price_unit': 10000.0,
            })],
        })
        self.assertEqual(order.salesperson_commission_amount, 800.0)

    def test_03_worksheet_aggregation_and_vendor_bill_settlement(self):
        """Test calculating commission worksheet lines and generating settlement vendor bill."""
        plan = self.env['commission.plan'].create({
            'name': 'Direct 10% Plan',
            'plan_type': 'flat',
            'calculation_basis': 'so_confirm',
            'flat_rate': 10.0,
            'enable_manager_override': False,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'user_id': self.sales_rep.id,
            'commission_plan_id': plan.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 5000.0,  # Total 10000 -> 10% = 1000
            })],
        })
        order.action_confirm()

        # Create Worksheet for current month
        today = fields.Date.context_today(order)
        ws = self.env['commission.worksheet'].create({
            'salesperson_id': self.sales_rep.id,
            'beneficiary_type': 'salesperson',
            'date_start': today,
            'date_end': today,
        })
        ws.action_calculate_commissions()
        self.assertEqual(ws.lines_count, 1)
        self.assertEqual(ws.total_commission_amount, 1000.0)
        self.assertEqual(ws.state, 'calculated')

        # Approve worksheet
        ws.action_approve()
        self.assertEqual(ws.state, 'approved')

        # Generate Vendor Bill via wizard
        wiz = self.env['commission.make.invoice.wizard'].with_context(active_id=ws.id).create({
            'worksheet_id': ws.id,
            'partner_id': self.sales_rep.partner_id.id,
        })
        wiz.action_create_vendor_bill()
        self.assertEqual(ws.state, 'settled')
        self.assertTrue(ws.vendor_bill_id)
        self.assertEqual(ws.vendor_bill_id.amount_total, 1000.0)
