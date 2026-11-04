# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    fixed_asset_id = fields.Many2one('fixed.asset', string='Fixed Asset', index='btree_not_null', copy=False,
                                     readonly=True)
    created_asset_count = fields.Integer(compute='_compute_created_asset_count')

    def _compute_created_asset_count(self):
        data = self.env['fixed.asset']._read_group(
            [('source_move_line_id.move_id', 'in', self.ids)], ['source_move_line_id'], ['__count'])
        counts = {}
        for move_line, count in data:
            counts[move_line.move_id.id] = counts.get(move_line.move_id.id, 0) + count
        for move in self:
            move.created_asset_count = counts.get(move.id, 0)

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        posted.filtered(lambda m: m.move_type == 'in_invoice')._create_assets_from_lines()
        return posted

    def _create_assets_from_lines(self):
        Asset = self.env['fixed.asset']
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.asset_category_id and l.display_type == 'product')
            if not lines:
                continue
            existing = Asset.search([('source_move_line_id', 'in', lines.ids)]).source_move_line_id
            for line in lines - existing:
                category = line.asset_category_id
                asset = Asset.create({
                    'name': line.name or line.product_id.display_name or move.name,
                    'category_id': category.id,
                    'company_id': move.company_id.id,
                    'partner_id': move.partner_id.id,
                    'acquisition_date': move.invoice_date or move.date,
                    'original_value': abs(line.balance),
                    'source_move_line_id': line.id,
                })
                asset.message_post(body=_('Asset created from vendor bill %s.', move._get_html_link()))
                if category.auto_confirm:
                    asset.action_confirm()

    def action_view_created_assets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('fixed_asset_depreciation_hub.action_fixed_asset')
        action['domain'] = [('source_move_line_id.move_id', '=', self.id)]
        action['context'] = {'create': False}
        return action


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    asset_category_id = fields.Many2one(
        'fixed.asset.category', string='Asset Category', check_company=True,
        help='When the vendor bill is posted, a fixed asset is created for this line.')
