# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SubscriptionPlan(models.Model):
    _name = 'subscription.plan'
    _description = 'Subscription Recurring Billing Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Plan Name', required=True, tracking=True)
    code = fields.Char(string='Code', copy=False)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id', readonly=True,
    )
    billing_interval = fields.Selection([
        ('day', 'Daily / Days'),
        ('week', 'Weekly / Weeks'),
        ('month', 'Monthly / Months'),
        ('year', 'Yearly / Years'),
    ], string='Billing Cycle Unit', default='month', required=True, tracking=True)
    billing_interval_count = fields.Integer(
        string='Interval Count', default=1, required=True,
        help='Frequency multiplier, e.g. 1 Month = Monthly, 3 Months = Quarterly, 1 Year = Annually.'
    )
    auto_invoice = fields.Boolean(
        string='Automated Invoice Generation', default=True,
        help='If checked, the daily scheduler automatically generates customer invoices on due dates.'
    )
    auto_post_invoice = fields.Boolean(
        string='Auto-Post Invoices', default=False,
        help='If enabled, created recurring invoices are validated automatically.'
    )
    reminder_days_before = fields.Integer(
        string='Expiration Alert (Days Before)', default=7,
        help='Number of days before contract expiry to trigger an activity notification.'
    )
    description = fields.Text(string='Internal Description')
    terms_conditions = fields.Html(string='Standard Terms & Conditions')

    contract_count = fields.Integer(
        string='Active Subscriptions', compute='_compute_contract_count',
    )

    def _compute_contract_count(self):
        contract_data = self.env['subscription.contract'].read_group(
            [('plan_id', 'in', self.ids), ('state', '!=', 'closed')],
            ['plan_id'], ['plan_id']
        )
        data_map = {d['plan_id'][0]: d['plan_id_count'] for d in contract_data}
        for plan in self:
            plan.contract_count = data_map.get(plan.id, 0)

    def action_view_contracts(self):
        self.ensure_one()
        return {
            'name': _('Contracts - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.contract',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }
