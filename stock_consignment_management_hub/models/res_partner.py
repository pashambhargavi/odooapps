# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    consignment_agreement_ids = fields.One2many(
        'consignment.agreement',
        'partner_id',
        string='Consignment Agreements'
    )
    consignment_agreement_count = fields.Integer(
        string='Consignment Agreements Count',
        compute='_compute_consignment_stats'
    )
    consignment_active_stock_value = fields.Monetary(
        string='Total Consigned Inventory Value',
        currency_field='currency_id',
        compute='_compute_consignment_stats'
    )

    @api.depends('consignment_agreement_ids.state', 'consignment_agreement_ids.total_active_stock_value')
    def _compute_consignment_stats(self):
        for partner in self:
            active_agrs = partner.consignment_agreement_ids.filtered(lambda a: a.state == 'active')
            partner.consignment_agreement_count = len(partner.consignment_agreement_ids)
            partner.consignment_active_stock_value = sum(active_agrs.mapped('total_active_stock_value'))

    def action_view_consignment_agreements(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_consignment_management_hub.action_consignment_agreement")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
