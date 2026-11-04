# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    rma_id = fields.Many2one('rma.order', string='Linked RMA', copy=False, index=True)
    rma_count = fields.Integer(string='RMA Count', compute='_compute_rma_count')

    def _compute_rma_count(self):
        for move in self:
            move.rma_count = self.env['rma.order'].search_count([
                '|', ('invoice_id', '=', move.id), ('credit_note_id', '=', move.id)
            ])

    def action_create_rma(self):
        self.ensure_one()
        lines = []
        default_reason = self.env['rma.reason'].search([], limit=1)
        for line in self.invoice_line_ids.filtered(lambda l: not l.display_type and l.quantity > 0):
            lines.append((0, 0, {
                'product_id': line.product_id.id,
                'ordered_qty': line.quantity,
                'delivered_qty': line.quantity,
                'return_qty': line.quantity,
                'unit_price': line.price_unit,
                'product_uom_id': line.product_uom_id.id if hasattr(line, 'product_uom_id') else line.product_id.uom_id.id,
                'reason_id': default_reason.id if default_reason else False,
            }))

        return {
            'name': _('Create RMA Return Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'rma.order',
            'view_mode': 'form',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_invoice_id': self.id,
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
            'domain': ['|', ('invoice_id', '=', self.id), ('credit_note_id', '=', self.id)],
        }
