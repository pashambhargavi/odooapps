# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class FixedAssetDisposeWizard(models.TransientModel):
    _name = 'fixed.asset.dispose.wizard'
    _description = 'Dispose Fixed Asset'

    asset_id = fields.Many2one('fixed.asset', required=True, readonly=True)
    currency_id = fields.Many2one(related='asset_id.currency_id')
    disposal_date = fields.Date(required=True, default=fields.Date.context_today)
    original_value = fields.Monetary(related='asset_id.original_value')
    depreciated_value = fields.Monetary(related='asset_id.depreciated_value')
    book_value = fields.Monetary(related='asset_id.book_value', string='Net Book Value (Loss)')

    def action_dispose(self):
        self.ensure_one()
        self.asset_id.action_dispose(self.disposal_date)
        return {'type': 'ir.actions.act_window_close'}
