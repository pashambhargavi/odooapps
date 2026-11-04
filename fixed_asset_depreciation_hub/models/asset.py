# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class FixedAsset(models.Model):
    _name = 'fixed.asset'
    _description = 'Fixed Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'acquisition_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Asset Name', required=True, tracking=True)
    reference = fields.Char(string='Reference / Tag', copy=False)
    category_id = fields.Many2one(
        'fixed.asset.category', string='Category', required=True, check_company=True, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id', string='Currency')
    partner_id = fields.Many2one('res.partner', string='Vendor')
    source_move_line_id = fields.Many2one(
        'account.move.line', string='Source Bill Line', copy=False, readonly=True, index='btree_not_null')
    source_move_id = fields.Many2one(related='source_move_line_id.move_id', string='Source Bill')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('close', 'Fully Depreciated'),
        ('disposed', 'Disposed'),
    ], default='draft', required=True, copy=False, tracking=True)

    acquisition_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    first_depreciation_date = fields.Date(
        compute='_compute_first_depreciation_date', store=True, precompute=True, readonly=False, required=True,
        help='Date from which depreciation starts (usually the date the asset is put in service).')
    original_value = fields.Monetary(string='Gross Value', required=True, tracking=True)
    salvage_value = fields.Monetary(
        string='Salvage Value', help='Value the asset is expected to keep at the end of its useful life.')

    method = fields.Selection(
        selection=[('linear', 'Linear (Straight Line)'), ('degressive', 'Declining Balance')],
        compute='_compute_method_values', store=True, precompute=True, readonly=False, required=True)
    degressive_factor = fields.Float(compute='_compute_method_values', store=True, precompute=True, readonly=False)
    method_number = fields.Integer(
        string='Number of Periods', compute='_compute_method_values', store=True, precompute=True, readonly=False, required=True)
    method_period = fields.Selection(
        [('1', 'Months'), ('12', 'Years')], string='Period Length',
        compute='_compute_method_values', store=True, precompute=True, readonly=False, required=True)
    prorata = fields.Boolean(string='Prorata Temporis', compute='_compute_method_values', store=True, precompute=True, readonly=False)

    line_ids = fields.One2many('fixed.asset.line', 'asset_id', string='Depreciation Board', copy=False)
    move_ids = fields.One2many('account.move', 'fixed_asset_id', string='Journal Entries', readonly=True)
    depreciated_value = fields.Monetary(compute='_compute_values', store=True, string='Posted Depreciation')
    value_residual = fields.Monetary(compute='_compute_values', store=True, string='Depreciable Residual')
    book_value = fields.Monetary(compute='_compute_values', store=True, string='Net Book Value')
    next_depreciation_date = fields.Date(compute='_compute_values', store=True)
    posted_line_count = fields.Integer(compute='_compute_values', store=True)
    move_count = fields.Integer(compute='_compute_move_count')

    disposal_date = fields.Date(readonly=True, copy=False)
    disposal_move_id = fields.Many2one('account.move', readonly=True, copy=False)
    note = fields.Html()

    # ------------------------------------------------------------------
    # Computes & constraints
    # ------------------------------------------------------------------
    @api.depends('acquisition_date')
    def _compute_first_depreciation_date(self):
        for asset in self:
            if not asset.first_depreciation_date:
                asset.first_depreciation_date = asset.acquisition_date

    @api.depends('category_id')
    def _compute_method_values(self):
        for asset in self:
            category = asset.category_id
            if not category:
                asset.method = asset.method or 'linear'
                asset.method_number = asset.method_number or 60
                asset.method_period = asset.method_period or '1'
                asset.degressive_factor = asset.degressive_factor or 2.0
                continue
            asset.method = category.method
            asset.degressive_factor = category.degressive_factor
            asset.method_number = category.method_number
            asset.method_period = category.method_period
            asset.prorata = category.prorata

    @api.depends('original_value', 'salvage_value', 'line_ids.amount', 'line_ids.move_posted', 'line_ids.date')
    def _compute_values(self):
        for asset in self:
            posted = asset.line_ids.filtered('move_posted')
            depreciated = sum(posted.mapped('amount'))
            asset.depreciated_value = depreciated
            asset.value_residual = asset.original_value - asset.salvage_value - depreciated
            asset.book_value = asset.original_value - depreciated
            asset.posted_line_count = len(posted)
            pending = (asset.line_ids - posted).sorted('date')
            asset.next_depreciation_date = pending[:1].date or False

    def _compute_move_count(self):
        for asset in self:
            asset.move_count = len(asset.move_ids)

    @api.constrains('original_value', 'salvage_value', 'method_number')
    def _check_values(self):
        for asset in self:
            if asset.original_value <= 0:
                raise ValidationError(_('The gross value of asset "%s" must be positive.', asset.name))
            if asset.salvage_value < 0 or asset.salvage_value >= asset.original_value:
                raise ValidationError(_(
                    'The salvage value of asset "%s" must be zero or positive and lower than its gross value.',
                    asset.name))
            if asset.method_number <= 0:
                raise ValidationError(_('The number of periods must be greater than zero.'))

    # ------------------------------------------------------------------
    # Depreciation board
    # ------------------------------------------------------------------
    def _period_end(self, date):
        self.ensure_one()
        if self.method_period == '12':
            return date.replace(month=12, day=31)
        return date + relativedelta(day=31)

    def _first_period_ratio(self):
        """Share of the first period that is depreciated (1.0 when prorata is disabled)."""
        self.ensure_one()
        if not self.prorata:
            return 1.0
        start = self.first_depreciation_date
        end = self._period_end(start)
        if self.method_period == '12':
            period_start = start.replace(month=1, day=1)
        else:
            period_start = start.replace(day=1)
        total_days = (end - period_start).days + 1
        return ((end - start).days + 1) / total_days

    def _compute_board_values(self):
        """Return a list of (date, amount) tuples for the full depreciation board."""
        self.ensure_one()
        currency = self.currency_id
        depreciable = self.original_value - self.salvage_value
        periods = self.method_number
        ratio = self._first_period_ratio()
        board_length = periods + (1 if float_compare(ratio, 1.0, precision_digits=6) < 0 else 0)
        months = int(self.method_period)

        residual = depreciable
        date = self._period_end(self.first_depreciation_date)
        result = []
        for index in range(board_length):
            if index == board_length - 1:
                amount = residual
            else:
                if self.method == 'linear':
                    amount = depreciable / periods
                else:
                    remaining_periods = max(periods - index, 1)
                    declining = residual * self.degressive_factor / periods
                    linear = residual / remaining_periods
                    amount = max(declining, linear)
                if index == 0:
                    amount *= ratio
            amount = currency.round(min(amount, residual))
            residual = currency.round(residual - amount)
            result.append((date, amount))
            if float_is_zero(residual, precision_rounding=currency.rounding):
                break
            date = date + relativedelta(months=months, day=31)
        return result

    def action_compute_board(self):
        for asset in self:
            if asset.state in ('close', 'disposed'):
                raise UserError(_('Asset "%s" is closed; its board cannot be recomputed.', asset.name))
            if asset.line_ids.filtered('move_posted'):
                raise UserError(_(
                    'Asset "%s" already has posted depreciation entries. '
                    'Reverse them before recomputing the board.', asset.name))
            asset.line_ids.unlink()
            cumulated = 0.0
            commands = []
            depreciable = asset.original_value - asset.salvage_value
            for sequence, (date, amount) in enumerate(asset._compute_board_values(), start=1):
                cumulated += amount
                commands.append(Command.create({
                    'sequence': sequence,
                    'date': date,
                    'amount': amount,
                    'depreciated_value': cumulated,
                    'remaining_value': depreciable - cumulated,
                }))
            asset.write({'line_ids': commands})
        return True

    # ------------------------------------------------------------------
    # State actions
    # ------------------------------------------------------------------
    def action_confirm(self):
        for asset in self:
            if asset.state != 'draft':
                continue
            asset.action_compute_board()
            asset.state = 'running'
            asset.message_post(body=_('Asset confirmed: %s depreciation lines scheduled.', len(asset.line_ids)))
        return True

    def action_set_to_draft(self):
        for asset in self:
            if asset.line_ids.filtered('move_posted'):
                raise UserError(_('Asset "%s" has posted entries and cannot be reset to draft.', asset.name))
            asset.line_ids.unlink()
            asset.state = 'draft'
        return True

    def action_post_due_lines(self):
        """Post every unposted line dated today or earlier."""
        today = fields.Date.context_today(self)
        lines = self.line_ids.filtered(lambda l: not l.move_id and l.date <= today)
        lines.sorted('date').action_post()
        return True

    def _check_closing(self):
        for asset in self:
            if asset.state == 'running' and asset.line_ids and all(asset.line_ids.mapped('move_posted')):
                asset.state = 'close'
                asset.message_post(body=_('Asset fully depreciated.'))

    def action_dispose(self, disposal_date):
        """Remove the asset from the books and book its net book value as a loss."""
        for asset in self:
            if asset.state not in ('running', 'close'):
                raise UserError(_('Only running or fully depreciated assets can be disposed.'))
            category = asset.category_id
            if not category.account_loss_id:
                raise UserError(_('Set a Disposal Loss Account on category "%s" first.', category.name))
            if asset.line_ids.filtered(lambda l: l.move_id and not l.move_posted):
                raise UserError(_('Asset "%s" has draft depreciation entries. Post or delete them first.',
                                  asset.name))
            asset.line_ids.filtered(lambda l: not l.move_id).unlink()
            currency = asset.currency_id
            depreciated = asset.depreciated_value
            loss = currency.round(asset.original_value - depreciated)
            label = _('Disposal: %s', asset.name)
            line_cmds = [Command.create({
                'name': label,
                'account_id': category.account_asset_id.id,
                'debit': 0.0,
                'credit': asset.original_value,
                'partner_id': asset.partner_id.id,
            })]
            if not float_is_zero(depreciated, precision_rounding=currency.rounding):
                line_cmds.append(Command.create({
                    'name': label,
                    'account_id': category.account_depreciation_id.id,
                    'debit': depreciated,
                    'credit': 0.0,
                    'partner_id': asset.partner_id.id,
                }))
            if not float_is_zero(loss, precision_rounding=currency.rounding):
                line_cmds.append(Command.create({
                    'name': label,
                    'account_id': category.account_loss_id.id,
                    'debit': loss,
                    'credit': 0.0,
                    'partner_id': asset.partner_id.id,
                }))
            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': category.journal_id.id,
                'date': disposal_date,
                'ref': label,
                'fixed_asset_id': asset.id,
                'line_ids': line_cmds,
            })
            move._post()
            asset.write({
                'state': 'disposed',
                'disposal_date': disposal_date,
                'disposal_move_id': move.id,
            })
            asset.message_post(body=_('Asset disposed on %(date)s. Loss booked: %(loss)s',
                                      date=disposal_date, loss=loss))
        return True

    def action_open_dispose_wizard(self):
        self.ensure_one()
        return {
            'name': _('Dispose Asset'),
            'type': 'ir.actions.act_window',
            'res_model': 'fixed.asset.dispose.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_asset_id': self.id},
        }

    def action_view_moves(self):
        self.ensure_one()
        return {
            'name': _('Journal Entries'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('fixed_asset_id', '=', self.id)],
            'context': {'create': False},
        }

    def unlink(self):
        for asset in self:
            if asset.state != 'draft':
                raise UserError(_('Only draft assets can be deleted. Dispose of "%s" instead.', asset.name))
        return super().unlink()

    @api.model
    def _cron_post_depreciation(self):
        today = fields.Date.context_today(self)
        lines = self.env['fixed.asset.line'].search([
            ('move_id', '=', False),
            ('date', '<=', today),
            ('asset_id.state', '=', 'running'),
        ], order='date, id')
        lines.action_post()
        return True
