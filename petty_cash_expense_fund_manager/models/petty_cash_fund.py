# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PettyCashFund(models.Model):
    _name = 'petty.cash.fund'
    _description = 'Petty Cash Float & Custodian Fund'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc, id desc'

    name = fields.Char(string='Fund Name', required=True, tracking=True)
    code = fields.Char(string='Fund Code', required=True, copy=False)
    custodian_id = fields.Many2one(
        'res.users',
        string='Accountable Custodian',
        required=True,
        tracking=True,
        help='User responsible for the physical cash float and vouchers.'
    )
    float_amount = fields.Monetary(
        string='Approved Float Amount',
        required=True,
        default=1000.0,
        currency_field='currency_id',
        tracking=True,
        help='Fixed imprest float amount allocated to this cash box.'
    )
    replenishment_threshold = fields.Monetary(
        string='Replenishment Alert Level',
        required=True,
        default=250.0,
        currency_field='currency_id',
        help='When cash balance drops to or below this amount, replenishment is required.'
    )
    current_balance = fields.Monetary(
        string='Current Cash in Box',
        compute='_compute_fund_balances',
        currency_field='currency_id',
        help='Calculated cash remaining in physical cash box.'
    )
    unreplenished_amount = fields.Monetary(
        string='Unreplenished Vouchers',
        compute='_compute_fund_balances',
        currency_field='currency_id'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Petty Cash Account',
        required=True,
        help='Balance Sheet asset account representing this petty cash float.'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string='Petty Cash Journal',
        required=True,
        domain="[('type', '=', 'cash')]",
        help='Cash journal used to record expense vouchers and reconciliations.'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft / Setup'),
        ('active', 'Active & Operational'),
        ('suspended', 'Suspended / Audit'),
        ('closed', 'Closed & Returned'),
    ], string='Status', default='draft', tracking=True)

    voucher_ids = fields.One2many(
        'petty.cash.voucher',
        'fund_id',
        string='Expense Vouchers'
    )
    replenishment_ids = fields.One2many(
        'petty.cash.replenishment',
        'fund_id',
        string='Replenishment Orders'
    )
    tally_ids = fields.One2many(
        'petty.cash.tally',
        'fund_id',
        string='Cash Count Tallies'
    )
    voucher_count = fields.Integer(compute='_compute_counts')
    replenishment_count = fields.Integer(compute='_compute_counts')
    tally_count = fields.Integer(compute='_compute_counts')

    @api.constrains('code', 'company_id')
    def _check_code_company_uniq(self):
        for fund in self:
            existing = self.search([
                ('id', '!=', fund.id),
                ('code', '=', fund.code),
                ('company_id', '=', fund.company_id.id),
            ])
            if existing:
                raise ValidationError(_("Petty Cash Fund Code '%s' must be unique per company!") % fund.code)

    @api.depends('float_amount', 'voucher_ids.state', 'voucher_ids.amount_total')
    def _compute_fund_balances(self):
        for fund in self:
            # Unreplenished vouchers are those paid from the box but not yet reimbursed by bank
            unreplenished = sum(
                v.amount_total for v in fund.voucher_ids if v.state == 'paid'
            )
            fund.unreplenished_amount = unreplenished
            fund.current_balance = fund.float_amount - unreplenished

    @api.depends('voucher_ids', 'replenishment_ids', 'tally_ids')
    def _compute_counts(self):
        for fund in self:
            fund.voucher_count = len(fund.voucher_ids)
            fund.replenishment_count = len(fund.replenishment_ids)
            fund.tally_count = len(fund.tally_ids)

    def action_activate(self):
        for fund in self:
            if fund.float_amount <= 0:
                raise UserError(_("Float amount must be greater than zero to activate the fund."))
            fund.state = 'active'
            fund.message_post(body=_("Petty Cash Fund '%s' is now active with float %s.") % (fund.name, fund.float_amount))

    def action_suspend(self):
        self.write({'state': 'suspended'})

    def action_close(self):
        for fund in self:
            unresolved = fund.voucher_ids.filtered(lambda v: v.state in ('draft', 'submitted', 'paid'))
            if unresolved:
                raise UserError(_("Cannot close fund '%s': There are %d unreplenished or pending vouchers.") % (fund.name, len(unresolved)))
            fund.state = 'closed'

    def action_view_vouchers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Vouchers: %s') % self.name,
            'res_model': 'petty.cash.voucher',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
            'context': {'default_fund_id': self.id},
        }

    def action_view_replenishments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Replenishment Orders: %s') % self.name,
            'res_model': 'petty.cash.replenishment',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
            'context': {'default_fund_id': self.id},
        }

    def action_view_tallies(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cash Count Tallies: %s') % self.name,
            'res_model': 'petty.cash.tally',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
            'context': {'default_fund_id': self.id},
        }

    def action_open_denomination_tally(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Physical Cash Count & Denomination Tally: %s') % self.name,
            'res_model': 'petty.cash.denomination.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_fund_id': self.id,
                'default_system_balance': self.current_balance,
            }
        }
