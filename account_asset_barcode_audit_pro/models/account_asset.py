# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AccountAssetProCategory(models.Model):
    _name = 'account.asset.pro.category'
    _description = 'Fixed Asset Pro Category'
    _order = 'name'

    name = fields.Char(string='Asset Category', required=True, translate=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    # Depreciation Calculation Parameters
    method = fields.Selection([
        ('straight_line', 'Straight-Line (Linear)'),
        ('degressive', 'Declining Balance (Degressive)'),
    ], string='Computation Method', required=True, default='straight_line')
    
    method_number = fields.Integer(string='Duration (Count)', default=36, required=True,
                                   help='Number of depreciation periods (e.g. 36 months, 5 years).')
    method_period = fields.Selection([
        ('1', 'Monthly'),
        ('3', 'Quarterly'),
        ('12', 'Annually'),
    ], string='Period Frequency', required=True, default='1')
    
    method_progress_factor = fields.Float(string='Degressive Factor', default=0.20,
                                          help='Applied to declining balance method (e.g. 0.20 = 20%).')
    prorata = fields.Boolean(string='Prorata Temporis', default=True,
                             help='Prorate the first depreciation amount based on acquisition date.')
    
    # Accounting Accounts & Journal
    journal_id = fields.Many2one('account.journal', string='Depreciation Journal', domain="[('type', '=', 'general')]", required=True)
    account_asset_id = fields.Many2one('account.account', string='Fixed Asset Account', required=True)
    account_depreciation_id = fields.Many2one('account.account', string='Accumulated Depreciation Account', required=True)
    account_expense_id = fields.Many2one('account.account', string='Depreciation Expense Account', required=True)
    account_gain_id = fields.Many2one('account.account', string='Gain on Disposal Account')
    account_loss_id = fields.Many2one('account.account', string='Loss on Disposal Account')


class AccountAssetPro(models.Model):
    _name = 'account.asset.pro'
    _description = 'Enterprise Fixed Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    code = fields.Char(string='Asset Code', readonly=True, copy=False, default=lambda self: _('New'))
    name = fields.Char(string='Asset Description', required=True, tracking=True)
    category_id = fields.Many2one('account.asset.pro.category', string='Asset Category', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)

    # Physical Audit & Barcode Attributes
    barcode = fields.Char(string='Barcode / Tag', copy=False, tracking=True,
                          help='Barcode or QR code printed on physical asset label.')
    serial_no = fields.Char(string='Serial Number', copy=False, tracking=True)
    model_no = fields.Char(string='Model / Part Number')
    location_name = fields.Char(string='Physical Location', tracking=True, default='HQ Building / Floor 1',
                                help='Building, Room, Bay, or Rack where the physical asset is stationed.')
    custodian_name = fields.Char(string='Custodian / Employee', tracking=True,
                                 help='Person or department responsible for asset custody.')

    # Financial & Acquisition Details
    vendor_id = fields.Many2one('res.partner', string='Vendor / Supplier')
    invoice_id = fields.Many2one('account.move', string='Purchase Invoice', domain="[('move_type', '=', 'in_invoice')]")
    acquisition_date = fields.Date(string='Acquisition Date', default=fields.Date.today, required=True, tracking=True)
    first_depreciation_date = fields.Date(string='First Depreciation Date', default=fields.Date.today, required=True)

    original_value = fields.Monetary(string='Gross Purchase Cost', required=True, tracking=True)
    salvage_value = fields.Monetary(string='Salvage / Residual Value', default=0.0, tracking=True)
    depreciable_value = fields.Monetary(string='Depreciable Base', compute='_compute_values', store=True)
    total_depreciated = fields.Monetary(string='Total Depreciated', compute='_compute_values', store=True)
    value_residual = fields.Monetary(string='Net Book Value (NBV)', compute='_compute_values', store=True, tracking=True)

    # Depreciation Rules (inherited or overridden from category)
    method = fields.Selection([
        ('straight_line', 'Straight-Line (Linear)'),
        ('degressive', 'Declining Balance (Degressive)'),
    ], string='Computation Method', required=True, default='straight_line')
    method_number = fields.Integer(string='Duration (Count)', default=36, required=True)
    method_period = fields.Selection([
        ('1', 'Monthly'),
        ('3', 'Quarterly'),
        ('12', 'Annually'),
    ], string='Period Frequency', required=True, default='1')
    method_progress_factor = fields.Float(string='Degressive Factor', default=0.20)
    prorata = fields.Boolean(string='Prorata Temporis', default=True)

    # Accounts overridden or defaulted from category
    journal_id = fields.Many2one('account.journal', string='Depreciation Journal', domain="[('type', '=', 'general')]")
    account_asset_id = fields.Many2one('account.account', string='Fixed Asset Account')
    account_depreciation_id = fields.Many2one('account.account', string='Accumulated Depreciation Account')
    account_expense_id = fields.Many2one('account.account', string='Depreciation Expense Account')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Running'),
        ('paused', 'Paused'),
        ('close', 'Fully Depreciated'),
        ('disposed', 'Disposed / Retired'),
    ], string='Status', required=True, default='draft', tracking=True)

    depreciation_line_ids = fields.One2many('account.asset.pro.depreciation.line', 'asset_id', string='Depreciation Board')

    # Audit Status Trackers
    last_audit_date = fields.Date(string='Last Physical Audit Date', readonly=True)
    last_audit_session_id = fields.Many2one('asset.audit.session', string='Last Audit Session', readonly=True)
    audit_status = fields.Selection([
        ('verified', 'Verified Present'),
        ('missing', 'Missing / Unaccounted'),
        ('wrong_location', 'Found in Wrong Location'),
        ('not_audited', 'Pending Audit'),
    ], string='Audit Physical Status', default='not_audited', tracking=True)

    # Disposal details
    disposal_date = fields.Date(string='Disposal Date', readonly=True)
    disposal_amount = fields.Monetary(string='Realized Sale Price', readonly=True)
    disposal_move_id = fields.Many2one('account.move', string='Disposal Accounting Entry', readonly=True)

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self.method = self.category_id.method
            self.method_number = self.category_id.method_number
            self.method_period = self.category_id.method_period
            self.method_progress_factor = self.category_id.method_progress_factor
            self.prorata = self.category_id.prorata
            self.journal_id = self.category_id.journal_id
            self.account_asset_id = self.category_id.account_asset_id
            self.account_depreciation_id = self.category_id.account_depreciation_id
            self.account_expense_id = self.category_id.account_expense_id

    @api.depends('original_value', 'salvage_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount')
    def _compute_values(self):
        for asset in self:
            asset.depreciable_value = max(0.0, asset.original_value - asset.salvage_value)
            posted_lines = asset.depreciation_line_ids.filtered(lambda l: l.move_check)
            asset.total_depreciated = sum(posted_lines.mapped('amount'))
            asset.value_residual = max(asset.salvage_value, asset.original_value - asset.total_depreciated)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('category_id'):
                cat = self.env['account.asset.pro.category'].browse(vals['category_id'])
                if cat:
                    if 'method' not in vals:
                        vals['method'] = cat.method
                    if 'method_number' not in vals:
                        vals['method_number'] = cat.method_number
                    if 'method_period' not in vals:
                        vals['method_period'] = cat.method_period
                    if 'method_progress_factor' not in vals:
                        vals['method_progress_factor'] = cat.method_progress_factor
                    if 'prorata' not in vals:
                        vals['prorata'] = cat.prorata
                    if 'journal_id' not in vals and cat.journal_id:
                        vals['journal_id'] = cat.journal_id.id
                    if 'account_asset_id' not in vals and cat.account_asset_id:
                        vals['account_asset_id'] = cat.account_asset_id.id
                    if 'account_depreciation_id' not in vals and cat.account_depreciation_id:
                        vals['account_depreciation_id'] = cat.account_depreciation_id.id
                    if 'account_expense_id' not in vals and cat.account_expense_id:
                        vals['account_expense_id'] = cat.account_expense_id.id

            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('account.asset.pro') or _('New')
            if not vals.get('barcode'):
                vals['barcode'] = vals['code']
        return super().create(vals_list)

    def compute_depreciation_board(self):
        """Generates the linear or declining balance depreciation schedule."""
        self.ensure_one()
        # Remove unposted lines
        unposted_lines = self.depreciation_line_ids.filtered(lambda l: not l.move_check)
        unposted_lines.unlink()

        if self.depreciable_value <= 0 or self.method_number <= 0:
            return True

        posted_amount = sum(self.depreciation_line_ids.filtered(lambda l: l.move_check).mapped('amount'))
        current_depreciable = self.depreciable_value - posted_amount
        remaining_periods = self.method_number - len(self.depreciation_line_ids.filtered(lambda l: l.move_check))

        if remaining_periods <= 0 or current_depreciable <= 0:
            return True

        lines = []
        months_step = int(self.method_period)
        cur_date = self.first_depreciation_date or fields.Date.today()
        current_book_value = self.original_value - posted_amount

        if self.method == 'straight_line':
            period_amount = round(current_depreciable / remaining_periods, 2)
            accumulated = posted_amount
            for i in range(1, remaining_periods + 1):
                if i == remaining_periods:
                    amount = max(0.0, round(self.depreciable_value - accumulated, 2))
                else:
                    amount = min(period_amount, round(self.depreciable_value - accumulated, 2))

                accumulated += amount
                current_book_value = max(self.salvage_value, self.original_value - accumulated)

                lines.append((0, 0, {
                    'sequence': i,
                    'depreciation_date': cur_date,
                    'amount': amount,
                    'depreciated_value': accumulated,
                    'remaining_value': current_book_value,
                }))
                cur_date = cur_date + relativedelta(months=months_step)

        elif self.method == 'degressive':
            factor = self.method_progress_factor or 0.20
            accumulated = posted_amount
            for i in range(1, remaining_periods + 1):
                if i == remaining_periods:
                    amount = max(0.0, round(self.depreciable_value - accumulated, 2))
                else:
                    amount = round((current_book_value - self.salvage_value) * factor, 2)
                    amount = min(amount, round(self.depreciable_value - accumulated, 2))

                accumulated += amount
                current_book_value = max(self.salvage_value, self.original_value - accumulated)

                lines.append((0, 0, {
                    'sequence': i,
                    'depreciation_date': cur_date,
                    'amount': amount,
                    'depreciated_value': accumulated,
                    'remaining_value': current_book_value,
                }))
                cur_date = cur_date + relativedelta(months=months_step)

        self.depreciation_line_ids = lines
        return True

    def action_confirm(self):
        for asset in self:
            if not asset.depreciation_line_ids:
                asset.compute_depreciation_board()
            asset.state = 'open'

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_resume(self):
        self.write({'state': 'open'})

    def action_post_depreciation_lines(self):
        """Posts all unposted depreciation lines up to current date."""
        today = fields.Date.today()
        for asset in self:
            due_lines = asset.depreciation_line_ids.filtered(lambda l: not l.move_check and l.depreciation_date <= today)
            for line in due_lines:
                line.action_post_line()

            if asset.value_residual <= asset.salvage_value:
                asset.state = 'close'

    def action_open_disposal_wizard(self):
        self.ensure_one()
        return {
            'name': _('Asset Disposal / Retirement'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.disposal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_id': self.id,
                'default_residual_value': self.value_residual,
            }
        }


class AccountAssetProDepreciationLine(models.Model):
    _name = 'account.asset.pro.depreciation.line'
    _description = 'Fixed Asset Depreciation Schedule Line'
    _order = 'depreciation_date, sequence'

    asset_id = fields.Many2one('account.asset.pro', string='Asset', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Period #', default=1)
    depreciation_date = fields.Date(string='Schedule Date', required=True)
    amount = fields.Monetary(string='Depreciation Amount', required=True)
    depreciated_value = fields.Monetary(string='Cumulative Depreciation', required=True)
    remaining_value = fields.Monetary(string='Remaining Book Value', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='asset_id.currency_id')

    move_id = fields.Many2one('account.move', string='Depreciation Entry', readonly=True)
    move_check = fields.Boolean(string='Posted', default=False, readonly=True)

    def action_post_line(self):
        self.ensure_one()
        if self.move_check:
            return True

        asset = self.asset_id
        journal = asset.journal_id or asset.category_id.journal_id
        exp_account = asset.account_expense_id or asset.category_id.account_expense_id
        dep_account = asset.account_depreciation_id or asset.category_id.account_depreciation_id

        if not journal or not exp_account or not dep_account:
            raise UserError(_("Please configure the Depreciation Journal, Expense Account, and Accumulated Depreciation Account on asset '%s' or its category.") % asset.name)

        move_vals = {
            'date': self.depreciation_date,
            'journal_id': journal.id,
            'ref': _('Depreciation: %s [%s] - Period %s') % (asset.name, asset.code, self.sequence),
            'line_ids': [
                (0, 0, {
                    'name': _('Depreciation Expense: %s') % asset.name,
                    'account_id': exp_account.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'name': _('Accumulated Depreciation: %s') % asset.name,
                    'account_id': dep_account.id,
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()

        self.write({
            'move_id': move.id,
            'move_check': True,
        })
        return True
