# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SubscriptionRenewWizard(models.TransientModel):
    _name = 'subscription.renew.wizard'
    _description = 'Subscription Contract Renewal & Extension Wizard'

    contract_id = fields.Many2one(
        'subscription.contract', string='Subscription Contract', required=True,
    )
    current_end_date = fields.Date(
        string='Current Expiration Date', readonly=True,
    )
    plan_id = fields.Many2one(
        'subscription.plan', string='Billing Plan',
    )
    renewal_type = fields.Selection([
        ('extend_cycle', 'Extend by Plan Cycle(s)'),
        ('fixed_date', 'Set Specific End Date'),
        ('indefinite', 'Renew Indefinitely (No End Date)'),
    ], string='Renewal Strategy', default='extend_cycle', required=True)

    cycles_to_extend = fields.Integer(
        string='Cycles to Extend', default=1,
    )
    new_end_date = fields.Date(
        string='New Expiration Date',
    )
    apply_price_adjustment = fields.Boolean(
        string='Apply Price Indexation / Adjustment (%)', default=False,
    )
    price_adjustment_percent = fields.Float(
        string='Adjustment Percentage (+/- %)', default=5.0,
    )

    @api.onchange('renewal_type', 'cycles_to_extend', 'current_end_date')
    def _onchange_renewal_calculation(self):
        if self.renewal_type == 'extend_cycle' and self.contract_id and self.contract_id.plan_id:
            plan = self.contract_id.plan_id
            base_date = self.current_end_date or fields.Date.context_today(self)
            count = (plan.billing_interval_count or 1) * (self.cycles_to_extend or 1)
            unit = plan.billing_interval or 'month'

            if unit == 'day':
                self.new_end_date = base_date + relativedelta(days=count)
            elif unit == 'week':
                self.new_end_date = base_date + relativedelta(weeks=count)
            elif unit == 'month':
                self.new_end_date = base_date + relativedelta(months=count)
            elif unit == 'year':
                self.new_end_date = base_date + relativedelta(years=count)
        elif self.renewal_type == 'indefinite':
            self.new_end_date = False

    def action_apply_renewal(self):
        self.ensure_one()
        contract = self.contract_id
        old_end = contract.date_end
        old_mrr = contract.mrr

        if self.renewal_type == 'extend_cycle':
            if not self.new_end_date:
                self._onchange_renewal_calculation()
            contract.date_end = self.new_end_date
        elif self.renewal_type == 'fixed_date':
            if not self.new_end_date:
                raise UserError(_('Please choose a valid New Expiration Date.'))
            contract.date_end = self.new_end_date
        elif self.renewal_type == 'indefinite':
            contract.date_end = False

        # Apply price adjustment if selected
        if self.apply_price_adjustment and self.price_adjustment_percent:
            multiplier = 1.0 + (self.price_adjustment_percent / 100.0)
            for line in contract.line_ids:
                line.price_unit = round(line.price_unit * multiplier, 2)

        # If next invoice date was passed or empty, reset to today
        if not contract.next_invoice_date or contract.next_invoice_date < fields.Date.context_today(self):
            contract.next_invoice_date = fields.Date.context_today(self)

        # If contract was expired, re-activate
        if contract.state == 'expired':
            contract.state = 'active'

        contract.message_post(
            body=_(
                'Subscription renewed successfully.<br/>'
                'Previous Expiration: %s &rarr; New Expiration: %s<br/>'
                'Status: %s | Price Adjustment: %s%%'
            ) % (
                old_end or _('None'),
                contract.date_end or _('Indefinite'),
                dict(contract._fields['state'].selection).get(contract.state),
                self.price_adjustment_percent if self.apply_price_adjustment else 0.0,
            )
        )
        return {'type': 'ir.actions.act_window_close'}
