# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    ncr_ids = fields.One2many('qms.ncr', 'purchase_order_id', string='Non-Conformance Reports')
    ncr_count = fields.Integer(string='NCR Count', compute='_compute_qms_ncr_count')

    @api.depends('ncr_ids')
    def _compute_qms_ncr_count(self):
        for po in self:
            po.ncr_count = len(po.ncr_ids)

    def action_view_qms_ncrs(self):
        self.ensure_one()
        action = self.env.ref('iso_quality_management_qms.action_qms_ncr').read()[0]
        action['domain'] = [('purchase_order_id', '=', self.id)]
        action['context'] = {
            'default_purchase_order_id': self.id,
            'default_partner_id': self.partner_id.id,
            'default_source_type': 'supplier',
        }
        return action
