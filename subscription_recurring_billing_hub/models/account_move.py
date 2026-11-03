# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        'subscription.contract', string='Origin Subscription',
        readonly=True, copy=False, index=True,
    )

    def action_view_origin_subscription(self):
        self.ensure_one()
        return {
            'name': _('Subscription Contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.contract',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
        }
