# -*- coding: utf-8 -*-
from odoo import models, fields


class SubscriptionPlanPro(models.Model):
    _name = 'subscription.plan.pro'
    _description = 'Subscription Billing Plan'
    _order = 'name'

    name = fields.Char(string='Plan Name', required=True, translate=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Billing Periodicity
    billing_interval = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly (3 Months)'),
        ('semi_annual', 'Semi-Annual (6 Months)'),
        ('annual', 'Annual (12 Months)'),
    ], string='Billing Interval', required=True, default='monthly')

    billing_interval_count = fields.Integer(string='Interval Multiplier', default=1, required=True,
                                           help='E.g. 1 Month, 2 Weeks, etc.')

    trial_period_days = fields.Integer(string='Free Trial Days', default=0,
                                       help='Number of initial free trial days before first billing.')
    grace_period_days = fields.Integer(string='Payment Grace Period (Days)', default=7,
                                       help='Number of days after due date before pausing service.')

    auto_renew = fields.Boolean(string='Auto-Renew Subscription', default=True)
    invoicing_journal_id = fields.Many2one('account.journal', string='Default Invoicing Journal', domain="[('type', '=', 'sale')]")


class SubscriptionCloseReason(models.Model):
    _name = 'subscription.close.reason'
    _description = 'Subscription Cancellation Reason'
    _order = 'sequence, name'

    name = fields.Char(string='Reason', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
