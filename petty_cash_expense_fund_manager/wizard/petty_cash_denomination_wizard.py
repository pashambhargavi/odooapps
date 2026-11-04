# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PettyCashDenominationWizard(models.TransientModel):
    _name = 'petty.cash.denomination.wizard'
    _description = 'Physical Cash Count Workbench Wizard'

    fund_id = fields.Many2one(
        'petty.cash.fund',
        string='Petty Cash Fund',
        required=True
    )
    currency_id = fields.Many2one(
        related='fund_id.currency_id',
        string='Currency'
    )
    system_balance = fields.Monetary(
        string='Expected Cash Balance',
        required=True,
        currency_field='currency_id'
    )
    count_1000 = fields.Integer(string='1000 Bills', default=0)
    count_500 = fields.Integer(string='500 Bills', default=0)
    count_100 = fields.Integer(string='100 Bills', default=0)
    count_50 = fields.Integer(string='50 Bills', default=0)
    count_20 = fields.Integer(string='20 Bills', default=0)
    count_10 = fields.Integer(string='10 Bills', default=0)
    count_5 = fields.Integer(string='5 Bills', default=0)
    count_1 = fields.Integer(string='1 Bills / Coins', default=0)
    count_coins = fields.Monetary(string='Loose Coins & Change', default=0.0, currency_field='currency_id')

    counted_total = fields.Monetary(
        string='Total Cash Counted',
        compute='_compute_totals',
        currency_field='currency_id'
    )
    discrepancy = fields.Monetary(
        string='Discrepancy (Over / Short)',
        compute='_compute_totals',
        currency_field='currency_id'
    )
    discrepancy_status = fields.Selection([
        ('match', 'Balanced (Exact Match)'),
        ('over', 'Cash Overage (+)'),
        ('short', 'Cash Shortage (-)'),
    ], string='Audit Verdict', compute='_compute_totals')

    notes = fields.Text(string='Auditor / Custodian Remarks')

    @api.depends('count_1000', 'count_500', 'count_100', 'count_50', 'count_20',
                 'count_10', 'count_5', 'count_1', 'count_coins', 'system_balance')
    def _compute_totals(self):
        for w in self:
            counted = (
                w.count_1000 * 1000.0 +
                w.count_500 * 500.0 +
                w.count_100 * 100.0 +
                w.count_50 * 50.0 +
                w.count_20 * 20.0 +
                w.count_10 * 10.0 +
                w.count_5 * 5.0 +
                w.count_1 * 1.0 +
                w.count_coins
            )
            w.counted_total = counted
            diff = counted - w.system_balance
            w.discrepancy = diff
            if abs(diff) < 0.001:
                w.discrepancy_status = 'match'
            elif diff > 0:
                w.discrepancy_status = 'over'
            else:
                w.discrepancy_status = 'short'

    def action_confirm_tally(self):
        self.ensure_one()
        tally = self.env['petty.cash.tally'].create({
            'fund_id': self.fund_id.id,
            'system_balance': self.system_balance,
            'count_1000': self.count_1000,
            'count_500': self.count_500,
            'count_100': self.count_100,
            'count_50': self.count_50,
            'count_20': self.count_20,
            'count_10': self.count_10,
            'count_5': self.count_5,
            'count_1': self.count_1,
            'count_coins': self.count_coins,
            'notes': self.notes,
            'state': 'verified',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cash Count Tally Result'),
            'res_model': 'petty.cash.tally',
            'res_id': tally.id,
            'view_mode': 'form',
            'target': 'current',
        }
