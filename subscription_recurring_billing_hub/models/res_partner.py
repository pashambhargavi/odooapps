# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    subscription_ids = fields.One2many(
        'subscription.contract', 'partner_id', string='Subscriptions',
    )
    subscription_count = fields.Integer(
        string='Subscriptions Count', compute='_compute_subscription_count',
    )

    def _compute_subscription_count(self):
        contract_data = self.env['subscription.contract'].read_group(
            [('partner_id', 'in', self.ids)],
            ['partner_id'], ['partner_id']
        )
        data_map = {d['partner_id'][0]: d['partner_id_count'] for d in contract_data}
        for partner in self:
            partner.subscription_count = data_map.get(partner.id, 0)

    def action_view_partner_subscriptions(self):
        self.ensure_one()
        return {
            'name': _('Subscriptions - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.contract',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }
