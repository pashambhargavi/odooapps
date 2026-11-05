# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    ncr_ids = fields.One2many('qms.ncr', 'stock_picking_id', string='Non-Conformance Reports')
    ncr_count = fields.Integer(string='NCR Count', compute='_compute_qms_ncr_count')

    @api.depends('ncr_ids')
    def _compute_qms_ncr_count(self):
        for picking in self:
            picking.ncr_count = len(picking.ncr_ids)

    def action_view_qms_ncrs(self):
        self.ensure_one()
        action = self.env.ref('iso_quality_management_qms.action_qms_ncr').read()[0]
        action['domain'] = [('stock_picking_id', '=', self.id)]
        action['context'] = {
            'default_stock_picking_id': self.id,
            'default_partner_id': self.partner_id.id if self.partner_id else False,
            'default_source_type': 'supplier' if self.picking_type_code == 'incoming' else 'internal',
        }
        return action
