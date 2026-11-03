# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import fields
from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestSubscriptionHub(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env['res.partner'].create({
            'name': 'Acme Enterprise SaaS Client',
            'email': 'acme@example.com',
        })
        cls.plan_monthly = cls.env['subscription.plan'].create({
            'name': 'Test Monthly Retainer',
            'code': 'TEST-M',
            'billing_interval': 'month',
            'billing_interval_count': 1,
            'auto_invoice': True,
        })
        cls.product_service = cls.env['product.product'].create({
            'name': 'Dedicated Cloud DevOps Support',
            'type': 'service',
            'list_price': 1500.0,
        })

    def test_01_subscription_lifecycle_and_mrr_calculation(self):
        """Test subscription activation, MRR/ARR normalization and pause/resume."""
        contract = self.env['subscription.contract'].create({
            'partner_id': self.customer.id,
            'plan_id': self.plan_monthly.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_service.id,
                'name': self.product_service.name,
                'quantity': 2.0,
                'price_unit': 1500.0,
            })],
        })

        self.assertEqual(contract.state, 'draft')
        self.assertEqual(contract.amount_untaxed, 3000.0)
        self.assertEqual(contract.mrr, 3000.0)
        self.assertEqual(contract.arr, 36000.0)

        # Activate
        contract.action_activate()
        self.assertEqual(contract.state, 'active')

        # Pause and Resume
        contract.action_pause()
        self.assertEqual(contract.state, 'paused')
        contract.action_resume()
        self.assertEqual(contract.state, 'active')

    def test_02_recurring_invoice_generation(self):
        """Test generating customer invoice directly from subscription."""
        today = fields.Date.context_today(self.env.user)
        contract = self.env['subscription.contract'].create({
            'partner_id': self.customer.id,
            'plan_id': self.plan_monthly.id,
            'date_start': today,
            'next_invoice_date': today,
            'line_ids': [(0, 0, {
                'product_id': self.product_service.id,
                'name': self.product_service.name,
                'quantity': 1.0,
                'price_unit': 1200.0,
            })],
        })
        contract.action_activate()

        # Generate invoice
        action = contract.action_generate_invoice()
        self.assertEqual(contract.invoice_count, 1)
        invoice = contract.invoice_ids[0]
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(invoice.amount_untaxed, 1200.0)
        self.assertEqual(contract.last_invoice_date, today)
        self.assertEqual(contract.next_invoice_date, today + relativedelta(months=1))

    def test_03_contract_renewal_wizard(self):
        """Test renewal wizard extending contract end date and adjusting price."""
        today = fields.Date.context_today(self.env.user)
        contract = self.env['subscription.contract'].create({
            'partner_id': self.customer.id,
            'plan_id': self.plan_monthly.id,
            'date_start': today,
            'date_end': today + relativedelta(months=1),
            'line_ids': [(0, 0, {
                'product_id': self.product_service.id,
                'name': self.product_service.name,
                'quantity': 1.0,
                'price_unit': 1000.0,
            })],
        })
        contract.action_activate()

        wizard = self.env['subscription.renew.wizard'].create({
            'contract_id': contract.id,
            'current_end_date': contract.date_end,
            'renewal_type': 'extend_cycle',
            'cycles_to_extend': 2,
            'apply_price_adjustment': True,
            'price_adjustment_percent': 10.0,
        })
        wizard.action_apply_renewal()

        self.assertEqual(contract.date_end, today + relativedelta(months=3))
        self.assertEqual(contract.line_ids[0].price_unit, 1100.0)

    def test_04_sale_order_conversion(self):
        """Test converting a confirmed sales order into a subscription contract."""
        order = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'subscription_plan_id': self.plan_monthly.id,
            'order_line': [(0, 0, {
                'product_id': self.product_service.id,
                'name': self.product_service.name,
                'product_uom_qty': 1.0,
                'price_unit': 800.0,
            })],
        })
        order.action_confirm()
        order.action_create_subscription()

        self.assertTrue(order.subscription_id)
        self.assertEqual(order.subscription_id.partner_id, self.customer)
        self.assertEqual(order.subscription_id.state, 'active')
        self.assertEqual(order.subscription_id.amount_untaxed, 800.0)
