# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    helpdesk_ticket_ids = fields.One2many('helpdesk.ticket', 'partner_id', string='Helpdesk Tickets')
    helpdesk_ticket_count = fields.Integer(
        string='Tickets Count',
        compute='_compute_helpdesk_ticket_count',
    )

    def _compute_helpdesk_ticket_count(self):
        data = self.env['helpdesk.ticket']._read_group(
            [('partner_id', 'child_of', self.ids)],
            ['partner_id'],
            ['__count'],
        )
        partner_counts = {partner.id: count for partner, count in data}
        for partner in self:
            partner.helpdesk_ticket_count = partner_counts.get(partner.id, 0)

    def action_view_helpdesk_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Support Tickets'),
            'res_model': 'helpdesk.ticket',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', 'child_of', self.id)],
            'context': {
                'default_partner_id': self.id,
            },
        }
