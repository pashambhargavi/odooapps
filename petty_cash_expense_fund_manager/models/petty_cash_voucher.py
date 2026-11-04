# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PettyCashVoucher(models.Model):
    _name = 'petty.cash.voucher'
    _description = 'Petty Cash Expense Voucher / Slip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Voucher Number', required=True, copy=False, default='/', tracking=True)
    fund_id = fields.Many2one(
        'petty.cash.fund',
        string='Petty Cash Fund',
        required=True,
        tracking=True,
        domain="[('state', '=', 'active')]"
    )
    custodian_id = fields.Many2one(
        related='fund_id.custodian_id',
        string='Fund Custodian',
        store=True
    )
    date = fields.Date(
        string='Voucher Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    payee = fields.Char(string='Payee / Beneficiary', required=True, tracking=True)
    partner_id = fields.Many2one(
        'res.partner',
        string='Claimant / Employee / Vendor',
        help='Optional partner or employee linked to this expense.'
    )
    line_ids = fields.One2many(
        'petty.cash.voucher.line',
        'voucher_id',
        string='Expense Lines',
        copy=True
    )
    amount_total = fields.Monetary(
        string='Total Voucher Amount',
        compute='_compute_amount_total',
        store=True,
        tracking=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='fund_id.currency_id',
        string='Currency',
        store=True
    )
    company_id = fields.Many2one(
        related='fund_id.company_id',
        string='Company',
        store=True
    )
    state = fields.Selection([
        ('draft', 'Draft Slip'),
        ('submitted', 'Submitted for Review'),
        ('approved', 'Approved by Custodian'),
        ('paid', 'Disbursed from Cash Box'),
        ('replenished', 'Reimbursed / Replenished'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    move_id = fields.Many2one(
        'account.move',
        string='Accounting Entry',
        copy=False,
        readonly=True
    )
    replenishment_id = fields.Many2one(
        'petty.cash.replenishment',
        string='Replenishment Order',
        copy=False,
        readonly=True
    )
    notes = fields.Text(string='Business Purpose / Notes')

    @api.depends('line_ids.amount')
    def _compute_amount_total(self):
        for v in self:
            v.amount_total = sum(line.amount for line in v.line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.voucher') or '/'
        return super().create(vals_list)

    def action_submit(self):
        for v in self:
            if not v.line_ids:
                raise UserError(_("Please add at least one expense line to the voucher."))
            if v.amount_total <= 0:
                raise UserError(_("Voucher total amount must be strictly positive."))
            if v.fund_id.state != 'active':
                raise UserError(_("The petty cash fund '%s' is not active.") % v.fund_id.name)
            if v.amount_total > v.fund_id.current_balance:
                raise UserError(
                    _("Insufficient Cash! Voucher amount (%s) exceeds current fund cash balance (%s).") %
                    (v.amount_total, v.fund_id.current_balance)
                )
            v.state = 'submitted'

    def action_approve(self):
        for v in self:
            if v.state != 'submitted':
                raise UserError(_("Only submitted vouchers can be approved."))
            v.state = 'approved'

    def action_pay(self):
        """Disburse cash from the box and post accounting journal entry."""
        for v in self:
            if v.state != 'approved':
                raise UserError(_("Only approved vouchers can be disbursed."))
            if v.amount_total > v.fund_id.current_balance:
                raise UserError(
                    _("Cannot disburse cash: Voucher amount (%s) exceeds available cash (%s).") %
                    (v.amount_total, v.fund_id.current_balance)
                )

            # Build Accounting Lines
            journal = v.fund_id.journal_id
            credit_account = v.fund_id.account_id
            move_lines = []

            # Credit Petty Cash Float
            move_lines.append((0, 0, {
                'name': _("Petty Cash Disbursed: %s - %s") % (v.name, v.payee),
                'account_id': credit_account.id,
                'debit': 0.0,
                'credit': v.amount_total,
                'partner_id': v.partner_id.id if v.partner_id else False,
            }))

            # Debit Expense Accounts for each line
            for line in v.line_ids:
                move_lines.append((0, 0, {
                    'name': line.name or _("Petty Cash Expense: %s") % v.name,
                    'account_id': line.account_id.id,
                    'debit': line.amount,
                    'credit': 0.0,
                    'partner_id': v.partner_id.id if v.partner_id else False,
                    'analytic_distribution': line.analytic_distribution if hasattr(line, 'analytic_distribution') and line.analytic_distribution else False,
                }))

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': journal.id,
                'date': v.date,
                'ref': _("Petty Cash: %s (%s)") % (v.name, v.payee),
                'line_ids': move_lines,
            })
            move.action_post()

            v.write({
                'move_id': move.id,
                'state': 'paid',
            })
            v.message_post(body=_("Cash disbursed: %s. Accounting Entry %s posted.") % (v.amount_total, move.name))

    def action_cancel(self):
        for v in self:
            if v.state == 'replenished':
                raise UserError(_("Cannot cancel a voucher that has already been replenished by bank."))
            if v.move_id:
                if v.move_id.state == 'posted':
                    v.move_id.button_draft()
                v.move_id.button_cancel()
            v.state = 'cancelled'

    def action_reset_draft(self):
        for v in self:
            if v.move_id and v.move_id.state == 'posted':
                raise UserError(_("Cannot reset to draft while posted journal entry exists."))
            v.state = 'draft'
