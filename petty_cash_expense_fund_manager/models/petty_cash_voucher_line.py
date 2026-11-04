# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class PettyCashVoucherLine(models.Model):
    _name = 'petty.cash.voucher.line'
    _description = 'Petty Cash Expense Line'

    voucher_id = fields.Many2one(
        'petty.cash.voucher',
        string='Voucher Reference',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Expense Item',
        help='Optional pre-configured expense product.'
    )
    name = fields.Char(string='Description / Purpose', required=True)
    account_id = fields.Many2one(
        'account.account',
        string='Expense Account',
        required=True,
        help='General ledger expense account debited for this expenditure.'
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='voucher_id.currency_id',
        string='Currency',
        store=True
    )
    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        help='Cost Center / Analytic Distribution for profitability tracking.'
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if not self.name:
                self.name = self.product_id.display_name
            # Auto-assign expense account from product or category
            acc = (
                self.product_id.property_account_expense_id
                or self.product_id.categ_id.property_account_expense_categ_id
            )
            if acc:
                self.account_id = acc
            if self.product_id.standard_price > 0 and self.amount == 0.0:
                self.amount = self.product_id.standard_price
