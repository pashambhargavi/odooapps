# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RmaOrderLine(models.Model):
    _name = 'rma.order.line'
    _description = 'RMA Return Order Line'
    _order = 'id'

    rma_id = fields.Many2one('rma.order', string='RMA Reference', required=True, ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    ordered_qty = fields.Float(string='Ordered Qty', default=1.0)
    delivered_qty = fields.Float(string='Delivered Qty', default=1.0)
    return_qty = fields.Float(string='Return Qty', default=1.0, required=True)
    unit_price = fields.Monetary(string='Unit Price', required=True, default=0.0)
    currency_id = fields.Many2one(related='rma_id.currency_id')
    refund_subtotal = fields.Monetary(string='Subtotal Refund', compute='_compute_subtotal', store=True)

    reason_id = fields.Many2one('rma.reason', string='Return Reason', required=True)
    action_type = fields.Selection([
        ('refund', 'Refund'),
        ('replacement', 'Replacement'),
        ('repair', 'Repair'),
        ('scrap', 'Scrap'),
    ], string='Action', default='refund', required=True)

    inspection_state = fields.Selection([
        ('pending', 'Pending Inspection'),
        ('passed', 'Quality Passed (Restock)'),
        ('repair', 'Needs Repair'),
        ('scrap', 'Scrapped / Defective'),
    ], string='Inspection Result', default='pending', copy=False)
    inspected_qty = fields.Float(string='Inspected Qty', copy=False)
    inspection_notes = fields.Char(string='Inspection Notes')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.lst_price

    @api.depends('return_qty', 'unit_price')
    def _compute_subtotal(self):
        for line in self:
            line.refund_subtotal = line.return_qty * line.unit_price

    @api.constrains('return_qty')
    def _check_return_qty(self):
        for line in self:
            if line.return_qty <= 0:
                raise ValidationError(_('Return quantity must be strictly greater than zero.'))
