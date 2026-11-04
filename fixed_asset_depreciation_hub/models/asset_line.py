# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class FixedAssetLine(models.Model):
    _name = 'fixed.asset.line'
    _description = 'Fixed Asset Depreciation Line'
    _order = 'asset_id, sequence, date'

    asset_id = fields.Many2one('fixed.asset', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=1)
    date = fields.Date(string='Depreciation Date', required=True)
    amount = fields.Monetary(string='Depreciation', required=True)
    depreciated_value = fields.Monetary(string='Cumulative Depreciation')
    remaining_value = fields.Monetary(string='Remaining Depreciable')
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, ondelete='set null', copy=False)
    move_posted = fields.Boolean(compute='_compute_move_posted', store=True)
    company_id = fields.Many2one(related='asset_id.company_id', store=True)
    currency_id = fields.Many2one(related='asset_id.currency_id')
    category_id = fields.Many2one(related='asset_id.category_id', store=True)
    asset_state = fields.Selection(related='asset_id.state', string='Asset Status')

    @api.depends('move_id.state')
    def _compute_move_posted(self):
        for line in self:
            line.move_posted = bool(line.move_id) and line.move_id.state == 'posted'

    def _prepare_move_vals(self):
        self.ensure_one()
        asset = self.asset_id
        category = asset.category_id
        label = _('%(asset)s: depreciation %(seq)s/%(total)s',
                  asset=asset.name, seq=self.sequence, total=len(asset.line_ids))
        return {
            'move_type': 'entry',
            'journal_id': category.journal_id.id,
            'date': self.date,
            'ref': label,
            'fixed_asset_id': asset.id,
            'line_ids': [
                Command.create({
                    'name': label,
                    'account_id': category.account_expense_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                    'partner_id': asset.partner_id.id,
                }),
                Command.create({
                    'name': label,
                    'account_id': category.account_depreciation_id.id,
                    'debit': 0.0,
                    'credit': self.amount,
                    'partner_id': asset.partner_id.id,
                }),
            ],
        }

    def action_post(self):
        for line in self.sorted(lambda l: (l.asset_id.id, l.date, l.sequence)):
            if line.move_id:
                continue
            if line.asset_id.state != 'running':
                raise UserError(_('Confirm asset "%s" before posting depreciation.', line.asset_id.name))
            earlier = line.asset_id.line_ids.filtered(lambda l: l.date < line.date and not l.move_id)
            if earlier:
                raise UserError(_('Post earlier depreciation lines of "%s" first.', line.asset_id.name))
            move = self.env['account.move'].create(line._prepare_move_vals())
            move._post()
            line.move_id = move
        self.asset_id._check_closing()
        return True

    def action_open_move(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }
