# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from odoo import fields
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestCreditOverdueMarginGuard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sales_user = cls.env['res.users'].create({
            'name': 'Test B2B Salesperson',
            'login': 'test_b2b_sales_user',
            'email': 'b2b_sales@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
                cls.env.ref('credit_overdue_margin_guard.group_credit_guard_user').id,
            ])],
        })
        cls.credit_controller = cls.env['res.users'].create({
            'name': 'Test Credit Controller',
            'login': 'test_credit_controller',
            'email': 'controller@example.com',
            'groups_id': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('sales_team.group_sale_salesman').id,
                cls.env.ref('credit_overdue_margin_guard.group_credit_guard_manager').id,
            ])],
        })
        cls.policy = cls.env['credit.risk.policy'].create({
            'name': 'Test Strict B2B Policy',
            'enforcement_mode': 'block',
            'default_credit_limit': 5000.0,
            'check_overdue_aging': True,
            'max_overdue_days': 30,
            'max_overdue_invoices': 2,
            'check_minimum_margin': True,
            'min_margin_percent': 20.0,
            'auto_confirm_on_override': True,
            'approver_ids': [(4, cls.credit_controller.id)],
        })
        cls.customer = cls.env['res.partner'].create({
            'name': 'Acme Industrial Corp',
            'credit_policy_id': cls.policy.id,
            'credit_enforcement_mode': 'policy',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Industrial Hydraulic Pump',
            'type': 'consu',
            'list_price': 1000.0,
            'standard_price': 600.0,
        })

    def test_01_healthy_order_confirms_directly(self):
        """An order within the $5,000 credit limit and >= 20% margin confirms without hold."""
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 1000.0,
            })],
        })
        # Unit cost = 600, price = 1000 -> Margin = 40% (>= 20% min), Total = 2000 (<= 5000 limit)
        self.assertAlmostEqual(order.order_margin_percent, 40.0, places=1)
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.risk_hold_state, 'clear')
        self.assertEqual(order.credit_override_count, 0)

    def test_02_low_margin_places_order_on_hold_and_override_approves(self):
        """An order below the 20% minimum profit margin is held until Finance approves the override."""
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2.0,
                'price_unit': 650.0,  # Cost is 600 -> Margin is 7.69% (< 20%)
            })],
        })
        order.action_confirm()
        # Should be blocked in draft state with risk_hold_state == 'on_hold'
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.risk_hold_state, 'on_hold')
        self.assertEqual(order.credit_override_count, 1)
        override_req = order.pending_override_id
        self.assertEqual(override_req.violation_type, 'low_margin')
        self.assertEqual(override_req.state, 'pending')

        # Non-controller salesperson cannot approve the override
        with self.assertRaises(AccessError):
            override_req.with_user(self.sales_user).action_approve()

        # Credit Controller approves -> order automatically confirms into 'sale'
        override_req.with_user(self.credit_controller).action_approve()
        self.assertEqual(override_req.state, 'approved')
        self.assertEqual(order.risk_hold_state, 'overridden')
        self.assertEqual(order.state, 'sale')

    def test_03_credit_limit_and_manual_hold_and_reject_wizard(self):
        """Exceeding credit limit or manual credit hold creates override request and supports rejection."""
        self.customer.write({
            'is_credit_hold': True,
            'credit_hold_reason': 'Pending bank guarantee verification',
        })
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 6.0,
                'price_unit': 1000.0,  # Total = 6000 (> 5000 limit) + manual credit hold
            })],
        })
        order.action_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.risk_hold_state, 'on_hold')
        override_req = order.pending_override_id
        self.assertEqual(override_req.violation_type, 'multiple')

        # Reject via wizard
        wiz = self.env['credit.override.reject.wizard'].with_user(self.credit_controller).create({
            'override_request_id': override_req.id,
            'rejection_reason': 'Require 50% wire prepayment before shipping.',
        })
        wiz.action_confirm_reject()
        self.assertEqual(override_req.state, 'rejected')
        self.assertEqual(order.risk_hold_state, 'rejected')
        self.assertIn('Require 50% wire prepayment', order.risk_violation_summary)
