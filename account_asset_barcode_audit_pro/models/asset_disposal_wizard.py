# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssetDisposalWizard(models.TransientModel):
    _name = 'asset.disposal.wizard'
    _description = 'Asset Disposal and Retirement Wizard'

    asset_id = fields.Many2one('account.asset.pro', string='Fixed Asset', required=True)
    disposal_date = fields.Date(string='Disposal Date', default=fields.Date.today, required=True)
    disposal_type = fields.Selection([
        ('sale', 'Sale to Third Party'),
        ('scrap', 'Scrap / Total Write-Off'),
        ('loss', 'Lost / Stolen / Casualty'),
    ], string='Disposal Mode', required=True, default='sale')

    sale_amount = fields.Monetary(string='Gross Proceeds / Sale Price', default=0.0)
    residual_value = fields.Monetary(string='Current Net Book Value (NBV)', readonly=True)
    gain_or_loss = fields.Monetary(string='Gain / (Loss) on Disposal', compute='_compute_gain_loss')
    currency_id = fields.Many2one('res.currency', string='Currency', related='asset_id.currency_id')

    journal_id = fields.Many2one('account.journal', string='Disposal Journal',
                                 domain="[('type', 'in', ('general', 'sale'))]", required=True)
    customer_id = fields.Many2one('res.partner', string='Buyer / Purchaser')
    account_gain_loss_id = fields.Many2one('account.account', string='Gain/Loss Account')
    notes = fields.Text(string='Disposal Justification & Authority')

    @api.depends('sale_amount', 'residual_value')
    def _compute_gain_loss(self):
        for wiz in self:
            wiz.gain_or_loss = wiz.sale_amount - wiz.residual_value

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id:
            self.residual_value = self.asset_id.value_residual
            self.journal_id = self.asset_id.journal_id or self.asset_id.category_id.journal_id
            if self.asset_id.category_id:
                self.account_gain_loss_id = self.asset_id.category_id.account_loss_id or self.asset_id.category_id.account_gain_id

    def action_confirm_disposal(self):
        self.ensure_one()
        asset = self.asset_id
        if asset.state == 'disposed':
            raise UserError(_("Asset '%s' is already disposed.") % asset.name)

        # Accounts
        asset_account = asset.account_asset_id or asset.category_id.account_asset_id
        dep_account = asset.account_depreciation_id or asset.category_id.account_depreciation_id
        gain_account = asset.category_id.account_gain_id or self.account_gain_loss_id
        loss_account = asset.category_id.account_loss_id or self.account_gain_loss_id

        if not asset_account or not dep_account:
            raise UserError(_("Please ensure Asset and Accumulated Depreciation accounts are configured."))

        gross_cost = asset.original_value
        accumulated_dep = sum(asset.depreciation_line_ids.filtered(lambda l: l.move_check).mapped('amount'))
        proceeds = self.sale_amount if self.disposal_type == 'sale' else 0.0
        nbv = gross_cost - accumulated_dep
        net_diff = proceeds - nbv

        lines = [
            # Credit Fixed Asset Account for gross historical cost
            (0, 0, {
                'name': _('Retire Asset Historical Cost: %s') % asset.name,
                'account_id': asset_account.id,
                'debit': 0.0,
                'credit': gross_cost,
            }),
            # Debit Accumulated Depreciation Account
            (0, 0, {
                'name': _('Reverse Accumulated Depreciation: %s') % asset.name,
                'account_id': dep_account.id,
                'debit': accumulated_dep,
                'credit': 0.0,
            }),
        ]

        # Proceeds line
        if proceeds > 0:
            bank_journal_account = self.journal_id.default_account_id
            if not bank_journal_account:
                bank_journal_account = self.env['account.account'].search([
                    ('account_type', 'in', ('asset_cash', 'asset_current')),
                    ('company_ids', 'in', [asset.company_id.id])
                ], limit=1)

            if bank_journal_account:
                lines.append((0, 0, {
                    'name': _('Disposal Proceeds: %s') % asset.name,
                    'account_id': bank_journal_account.id,
                    'debit': proceeds,
                    'credit': 0.0,
                }))

        # Gain or Loss
        if net_diff > 0:
            # Gain on Disposal (Credit)
            if not gain_account:
                gain_account = self.env['account.account'].search([
                    ('account_type', '=', 'income_other'),
                    ('company_ids', 'in', [asset.company_id.id])
                ], limit=1)
            if gain_account:
                lines.append((0, 0, {
                    'name': _('Gain on Disposal: %s') % asset.name,
                    'account_id': gain_account.id,
                    'debit': 0.0,
                    'credit': net_diff,
                }))
        elif net_diff < 0:
            # Loss on Disposal (Debit)
            loss_amount = abs(net_diff)
            if not loss_account:
                loss_account = self.env['account.account'].search([
                    ('account_type', '=', 'expense'),
                    ('company_ids', 'in', [asset.company_id.id])
                ], limit=1)
            if loss_account:
                lines.append((0, 0, {
                    'name': _('Loss on Asset Disposal: %s') % asset.name,
                    'account_id': loss_account.id,
                    'debit': loss_amount,
                    'credit': 0.0,
                }))

        move = self.env['account.move'].create({
            'date': self.disposal_date,
            'journal_id': self.journal_id.id,
            'ref': _('Asset Disposal: %s [%s]') % (asset.name, asset.code),
            'line_ids': lines,
        })
        move.action_post()

        # Unlink any future unposted depreciation lines
        asset.depreciation_line_ids.filtered(lambda l: not l.move_check).unlink()

        asset.write({
            'state': 'disposed',
            'disposal_date': self.disposal_date,
            'disposal_amount': proceeds,
            'disposal_move_id': move.id,
        })
        return True
