# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo.tests.common import TransactionCase
from odoo import fields


class TestSubscriptionRecurringBillingPro(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Customer Partner
        cls.partner = cls.env['res.partner'].create({
            'name': 'Acme Enterprise Global Corp',
            'email': 'billing@acme-global.com',
        })

        # Sales Journal
        cls.journal_sale = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', cls.company.id)
        ], limit=1)
        if not cls.journal_sale:
            cls.journal_sale = cls.env['account.journal'].create({
                'name': 'Subscription Customer Invoices',
                'code': 'SUBINV',
                'type': 'sale',
                'company_id': cls.company.id,
            })

        # Products
        cls.product_saas = cls.env['product.product'].create({
            'name': 'Cloud Platform Enterprise Seat',
            'type': 'service',
            'list_price': 100.0,
        })
        cls.product_support = cls.env['product.product'].create({
            'name': '24/7 Premium SLA Support',
            'type': 'service',
            'list_price': 500.0,
        })

        # Monthly Plan
        cls.plan_monthly = cls.env['subscription.plan.pro'].create({
            'name': 'Enterprise Monthly SaaS Plan',
            'billing_interval': 'monthly',
            'billing_interval_count': 1,
            'trial_period_days': 14,
            'auto_renew': True,
            'invoicing_journal_id': cls.journal_sale.id,
            'company_id': cls.company.id,
        })

        # Annual Plan
        cls.plan_annual = cls.env['subscription.plan.pro'].create({
            'name': 'Enterprise Annual SaaS Plan',
            'billing_interval': 'annual',
            'billing_interval_count': 1,
            'trial_period_days': 0,
            'auto_renew': True,
            'invoicing_journal_id': cls.journal_sale.id,
            'company_id': cls.company.id,
        })

    def test_01_plan_and_subscription_creation(self):
        """Verify plan configuration and initial subscription draft creation."""
        sub = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': fields.Date.today(),
            'line_ids': [
                (0, 0, {
                    'product_id': self.product_saas.id,
                    'name': self.product_saas.name,
                    'quantity': 10.0,
                    'price_unit': 100.0,
                }),
                (0, 0, {
                    'product_id': self.product_support.id,
                    'name': self.product_support.name,
                    'quantity': 1.0,
                    'price_unit': 500.0,
                })
            ]
        })

        self.assertTrue(sub.name.startswith('SUB/'))
        self.assertEqual(sub.state, 'draft')
        self.assertEqual(sub.recurring_total, 1500.0)

    def test_02_revenue_metrics_mrr_arr(self):
        """Verify Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR) calculations."""
        # Monthly: $1,500/mo -> MRR = $1,500, ARR = $18,000
        sub_m = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_saas.id,
                'name': self.product_saas.name,
                'quantity': 15.0,
                'price_unit': 100.0,
            })]
        })
        self.assertEqual(sub_m.recurring_mrr, 1500.0)
        self.assertEqual(sub_m.recurring_arr, 18000.0)

        # Annual: $12,000/yr -> MRR = $1,000, ARR = $12,000
        sub_a = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_annual.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_saas.id,
                'name': self.product_saas.name,
                'quantity': 10.0,
                'price_unit': 1200.0,
            })]
        })
        self.assertEqual(sub_a.recurring_total, 12000.0)
        self.assertEqual(sub_a.recurring_mrr, 1000.0)
        self.assertEqual(sub_a.recurring_arr, 12000.0)

    def test_03_subscription_activation_and_trial(self):
        """Verify 14-day trial period handling upon activation."""
        sub = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_monthly.id,
            'start_date': fields.Date.today(),
            'line_ids': [(0, 0, {
                'product_id': self.product_saas.id,
                'name': self.product_saas.name,
                'quantity': 5.0,
                'price_unit': 100.0,
            })]
        })

        sub.action_start()
        self.assertEqual(sub.state, 'trial')
        self.assertTrue(sub.trial_end_date)
        self.assertEqual(sub.next_invoice_date, sub.trial_end_date)

    def test_04_invoice_generation_and_date_advancement(self):
        """Verify recurring invoice generation advances next_invoice_date and links invoice."""
        today = fields.Date.today()
        sub = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_annual.id,
            'start_date': today,
            'next_invoice_date': today,
            'line_ids': [(0, 0, {
                'product_id': self.product_saas.id,
                'name': self.product_saas.name,
                'quantity': 2.0,
                'price_unit': 1200.0,
            })]
        })
        sub.action_start()
        self.assertEqual(sub.state, 'active')

        # Generate Invoice
        invoice = sub.action_generate_invoice()
        self.assertTrue(invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(invoice.amount_untaxed, 2400.0)
        self.assertEqual(sub.invoice_count, 1)

        # Date should advance by 1 year
        expected_next = today + relativedelta(years=1)
        self.assertEqual(sub.next_invoice_date, expected_next)

    def test_05_cron_automated_billing_batch(self):
        """Verify scheduled cron generates invoices for all due subscriptions."""
        today = fields.Date.today()
        sub = self.env['subscription.pro'].create({
            'partner_id': self.partner.id,
            'plan_id': self.plan_annual.id,
            'start_date': today,
            'next_invoice_date': today,
            'line_ids': [(0, 0, {
                'product_id': self.product_support.id,
                'name': self.product_support.name,
                'quantity': 1.0,
                'price_unit': 500.0,
            })]
        })
        sub.action_start()
        self.assertEqual(sub.invoice_count, 0)

        # Run automated batch cron
        self.env['subscription.pro']._cron_generate_recurring_invoices()
        self.assertEqual(sub.invoice_count, 1)
