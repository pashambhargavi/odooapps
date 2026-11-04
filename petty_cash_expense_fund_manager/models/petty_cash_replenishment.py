# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PettyCashReplenishment(models.Model):
    _name = 'petty.cash.replenishment'
    _description = 'Petty Cash Imprest Replenishment Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Replenishment Ref', required=True, copy=False, default='/', tracking=True)
    fund_id = fields.Many2one(
        'petty.cash.fund',
        string='Petty Cash Fund',
        required=True,
        tracking=True,
        domain="[('state', '=', 'active')]"
    )
    custodian_id = fields.Many2one(
        related='fund_id.custodian_id',
        string='Custodian',
        store=True
    )
    date = fields.Date(
        string='Request Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True
    )
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Source Bank / Disbursing Journal',
        required=True,
        domain="[('type', 'in', ('bank', 'cash'))]",
        help='Bank account or main cash desk transferring cash to replenish the petty cash float.'
    )
    voucher_ids = fields.Many2many(
        'petty.cash.voucher',
        'replenishment_voucher_rel',
        'replenishment_id',
        'voucher_id',
        string='Vouchers to Reimburse',
        domain="[('fund_id', '=', fund_id), ('state', '=', 'paid')]"
    )
    total_reimbursement = fields.Monetary(
        string='Total Reimbursement Amount',
        compute='_compute_total',
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
        ('draft', 'Draft Request'),
        ('submitted', 'Submitted to Treasury'),
        ('approved', 'Approved by Finance'),
        ('reimbursed', 'Reimbursed / Funded'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, copy=False)

    move_id = fields.Many2one(
        'account.move',
        string='Bank Transfer Entry',
        copy=False,
        readonly=True
    )
    notes = fields.Text(string='Reimbursement Justification / Remarks')

    @api.depends('voucher_ids.amount_total')
    def _compute_total(self):
        for rep in self:
            rep.total_reimbursement = sum(v.amount_total for v in rep.voucher_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.replenishment') or '/'
        return super().create(vals_list)

    @api.onchange('fund_id')
    def _onchange_fund_id(self):
        if self.fund_id:
            # Auto-populate all paid vouchers pending replenishment for this fund
            paid_vouchers = self.env['petty.cash.voucher'].search([
                ('fund_id', '=', self.fund_id.id),
                ('state', '=', 'paid'),
            ])
            self.voucher_ids = paid_vouchers

    def action_submit(self):
        for rep in self:
            if not rep.voucher_ids:
                raise UserError(_("Please attach at least one paid voucher for replenishment."))
            if rep.total_reimbursement <= 0:
                raise UserError(_("Reimbursement amount must be greater than zero."))
            rep.state = 'submitted'

    def action_approve(self):
        for rep in self:
            if rep.state != 'submitted':
                raise UserError(_("Only submitted requests can be approved."))
            rep.state = 'approved'

    def action_reimburse(self):
        """Execute bank transfer journal entry and restore float balance."""
        for rep in self:
            if rep.state != 'approved':
                raise UserError(_("Only approved requests can be reimbursed."))

            fund_debit_account = rep.fund_id.account_id
            bank_credit_account = (
                rep.bank_journal_id.default_account_id
                or rep.bank_journal_id.suspense_account_id
            )
            if not bank_credit_account:
                raise UserError(_("Source bank journal '%s' does not have a default account configured.") % rep.bank_journal_id.name)

            move_lines = [
                # Debit Petty Cash Float Account (restoring cash balance)
                (0, 0, {
                    'name': _("Petty Cash Replenishment: %s") % rep.name,
                    'account_id': fund_debit_account.id,
                    'debit': rep.total_reimbursement,
                    'credit': 0.0,
                }),
                # Credit Bank / Source Account (disbursing funds)
                (0, 0, {
                    'name': _("Bank Transfer to Petty Cash: %s (%s)") % (rep.fund_id.name, rep.name),
                    'account_id': bank_credit_account.id,
                    'debit': 0.0,
                    'credit': rep.total_reimbursement,
                }),
            ]

            move = self.env['account.move'].create({
                'move_type': 'entry',
                'journal_id': rep.bank_journal_id.id,
                'date': rep.date,
                'ref': _("Replenishment: %s - %s") % (rep.name, rep.fund_id.name),
                'line_ids': move_lines,
            })
            move.action_post()

            # Mark all vouchers as replenished
            for voucher in rep.voucher_ids:
                voucher.write({
                    'state': 'replenished',
                    'replenishment_id': rep.id,
                })

            rep.write({
                'move_id': move.id,
                'state': 'reimbursed',
            })

            rep.message_post(body=_(
                "Replenishment executed: %s transferred from %s. Journal Entry: %s. Float restored to full capacity."
            ) % (rep.total_reimbursement, rep.bank_journal_id.name, move.name))

    def action_cancel(self):
        for rep in self:
            if rep.state == 'reimbursed':
                raise UserError(_("Cannot cancel an already executed bank reimbursement."))
            rep.state = 'cancelled'
