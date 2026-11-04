# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PettyCashTally(models.Model):
    _name = 'petty.cash.tally'
    _description = 'Physical Cash Count & Denomination Tally'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tally_date desc, id desc'

    name = fields.Char(string='Tally Ref', required=True, copy=False, default='/')
    fund_id = fields.Many2one(
        'petty.cash.fund',
        string='Petty Cash Fund',
        required=True,
        tracking=True
    )
    custodian_id = fields.Many2one(
        related='fund_id.custodian_id',
        string='Custodian',
        store=True
    )
    tally_date = fields.Datetime(
        string='Tally Date & Time',
        default=fields.Datetime.now,
        required=True,
        tracking=True
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

    # Denomination counts
    count_1000 = fields.Integer(string='1000 Bills', default=0)
    count_500 = fields.Integer(string='500 Bills', default=0)
    count_100 = fields.Integer(string='100 Bills', default=0)
    count_50 = fields.Integer(string='50 Bills', default=0)
    count_20 = fields.Integer(string='20 Bills', default=0)
    count_10 = fields.Integer(string='10 Bills', default=0)
    count_5 = fields.Integer(string='5 Bills', default=0)
    count_1 = fields.Integer(string='1 Bills / Coins', default=0)
    count_coins = fields.Monetary(string='Loose Coins & Small Change', default=0.0, currency_field='currency_id')

    counted_total = fields.Monetary(
        string='Total Counted Cash',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    system_balance = fields.Monetary(
        string='Expected System Balance',
        required=True,
        currency_field='currency_id',
        tracking=True
    )
    discrepancy = fields.Monetary(
        string='Discrepancy (Over / Short)',
        compute='_compute_totals',
        store=True,
        currency_field='currency_id',
        tracking=True
    )
    discrepancy_status = fields.Selection([
        ('match', 'Balanced (Exact Match)'),
        ('over', 'Cash Overage (+)'),
        ('short', 'Cash Shortage (-)'),
    ], string='Audit Result', compute='_compute_totals', store=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft Tally'),
        ('verified', 'Verified by Custodian'),
        ('approved', 'Approved by Auditor / Manager'),
    ], string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Auditor Comments / Discrepancy Explanation')

    @api.depends('count_1000', 'count_500', 'count_100', 'count_50', 'count_20',
                 'count_10', 'count_5', 'count_1', 'count_coins', 'system_balance')
    def _compute_totals(self):
        for t in self:
            counted = (
                t.count_1000 * 1000.0 +
                t.count_500 * 500.0 +
                t.count_100 * 100.0 +
                t.count_50 * 50.0 +
                t.count_20 * 20.0 +
                t.count_10 * 10.0 +
                t.count_5 * 5.0 +
                t.count_1 * 1.0 +
                t.count_coins
            )
            t.counted_total = counted
            diff = counted - t.system_balance
            t.discrepancy = diff
            if abs(diff) < 0.001:
                t.discrepancy_status = 'match'
            elif diff > 0:
                t.discrepancy_status = 'over'
            else:
                t.discrepancy_status = 'short'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', '/') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.tally') or '/'
        return super().create(vals_list)

    def action_verify(self):
        for t in self:
            t.state = 'verified'

    def action_approve(self):
        for t in self:
            t.state = 'approved'
            t.message_post(body=_(
                "Cash count audited and approved. Counted: %s, Expected: %s, Discrepancy: %s (%s)"
            ) % (t.counted_total, t.system_balance, t.discrepancy, t.discrepancy_status))
