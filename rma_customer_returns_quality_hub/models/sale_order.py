# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    rma_count = fields.Integer(string='RMA Count', compute='_compute_rma_count')

    def _compute_rma_count(self):
        for order in self:
            order.rma_count = self.env['rma.order'].search_count([('sale_id', '=', order.id)])

    def action_create_rma(self):
        self.ensure_one()
        lines = []
        default_reason = self.env['rma.reason'].search([], limit=1)
        for line in self.order_line.filtered(lambda l: not l.display_type and l.qty_delivered > 0):
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'ordered_qty': line.product_uom_qty,
                'delivered_qty': line.qty_delivered,
                'return_qty': line.qty_delivered,
                'unit_price': line.price_unit,
                'product_uom_id': line.product_uom.id,
                'reason_id': default_reason.id if default_reason else False,
            }))

        picking = self.picking_ids.filtered(lambda p: p.state == 'done')[:1]

        return {
            'name': _('Create RMA Return Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'rma.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_sale_id': self.id,
                'default_picking_id': picking.id if picking else False,
                'default_company_id': self.company_id.id,
                'default_line_ids': lines,
            },
        }

    def action_view_rmas(self):
        self.ensure_one()
        return {
            'name': _('RMA Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'rma.order',
            'view_mode': 'list,form',
            'domain': [('sale_id', '=', self.id)],
            'context': {'default_sale_id': self.id, 'default_partner_id': self.partner_id.id},
        }
