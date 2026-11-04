# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    rma_id = fields.Many2one('rma.order', string='Linked RMA', copy=False, index=True)
    rma_count = fields.Integer(string='RMA Count', compute='_compute_rma_count')

    def _compute_rma_count(self):
        for picking in self:
            picking.rma_count = self.env['rma.order'].search_count([
                '|', ('picking_id', '=', picking.id), ('return_picking_id', '=', picking.id)
            ])

    def action_create_rma(self):
        self.ensure_one()
        lines = []
        default_reason = self.env['rma.reason'].search([], limit=1)
        for move in self.move_ids.filtered(lambda m: m.quantity > 0):
            lines.append((0, 0, {
                'product_id': move.product_id.id,
                'ordered_qty': move.product_uom_qty,
                'delivered_qty': move.quantity,
                'return_qty': move.quantity,
                'unit_price': move.product_id.lst_price,
                'product_uom_id': move.product_uom.id,
                'reason_id': default_reason.id if default_reason else False,
            }))

        return {
            'name': _('Create RMA Return Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'rma.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_picking_id': self.id,
                'default_sale_id': self.sale_id.id if hasattr(self, 'sale_id') and self.sale_id else False,
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
            'domain': ['|', ('picking_id', '=', self.id), ('return_picking_id', '=', self.id)],
        }
