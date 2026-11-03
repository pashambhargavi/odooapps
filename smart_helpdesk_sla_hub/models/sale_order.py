# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    helpdesk_ticket_ids = fields.One2many('helpdesk.ticket', 'sale_order_id', string='Support Tickets')
    helpdesk_ticket_count = fields.Integer(
        string='Tickets Count',
        compute='_compute_helpdesk_ticket_count',
    )

    def _compute_helpdesk_ticket_count(self):
        data = self.env['helpdesk.ticket']._read_group(
            [('sale_order_id', 'in', self.ids)],
            ['sale_order_id'],
            ['__count'],
        )
        order_counts = {order.id: count for order, count in data}
        for order in self:
            order.helpdesk_ticket_count = order_counts.get(order.id, 0)

    def action_view_helpdesk_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Support Tickets - %s') % self.name,
            'res_model': 'helpdesk.ticket',
            'view_mode': 'kanban,list,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_name': _('Support for Order %s') % self.name,
            },
        }
