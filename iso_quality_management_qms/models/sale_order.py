# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ncr_ids = fields.One2many('qms.ncr', 'sale_order_id', string='Customer Complaint Reports')
    ncr_count = fields.Integer(string='NCR Count', compute='_compute_qms_ncr_count')

    @api.depends('ncr_ids')
    def _compute_qms_ncr_count(self):
        for order in self:
            order.ncr_count = len(order.ncr_ids)

    def action_view_qms_ncrs(self):
        self.ensure_one()
        action = self.env.ref('iso_quality_management_qms.action_qms_ncr').read()[0]
        action['domain'] = [('sale_order_id', '=', self.id)]
        action['context'] = {
            'default_sale_order_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_source_type': 'customer',
        }
        return action
