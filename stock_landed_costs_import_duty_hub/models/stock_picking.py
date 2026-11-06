# -*- coding: utf-8 -*-
from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    landed_cost_ids = fields.Many2many(
        'stock.landed.cost.hub',
        'stock_landed_cost_hub_picking_rel',
        'picking_id',
        'cost_id',
        string='Landed Costs',
        readonly=True
    )
    landed_cost_count = fields.Integer(
        string='Landed Costs Count',
        compute='_compute_landed_cost_count'
    )

    @api.depends('landed_cost_ids')
    def _compute_landed_cost_count(self):
        for record in self:
            record.landed_cost_count = len(record.landed_cost_ids)

    def action_view_landed_costs(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock_landed_costs_import_duty_hub.action_stock_landed_cost_hub')
        action['domain'] = [('id', 'in', self.landed_cost_ids.ids)]
        action['context'] = {'default_picking_ids': [(4, self.id)]}
        return action
