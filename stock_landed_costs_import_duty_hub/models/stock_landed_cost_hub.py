# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

SPLIT_METHODS = [
    ('equal', 'Equal Split'),
    ('by_quantity', 'By Quantity'),
    ('by_current_cost_price', 'By Current Cost / Value'),
    ('by_weight', 'By Gross Weight'),
    ('by_volume', 'By Volume')
]


class StockLandedCostHub(models.Model):
    _name = 'stock.landed.cost.hub'
    _description = 'Landed Cost & Import Duty Hub'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True
    )
    date = fields.Date(
        string='Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Company Currency',
        related='company_id.currency_id',
        readonly=True
    )
    account_journal_id = fields.Many2one(
        'account.journal',
        string='Accounting Journal',
        domain="[('type', '=', 'general')]",
        help='Journal where valuation adjustment entries are booked.'
    )
    account_move_id = fields.Many2one(
        'account.move',
        string='Valuation Journal Entry',
        readonly=True,
        copy=False,
        help='Generated accounting entry for this landed cost.'
    )
    picking_ids = fields.Many2many(
        'stock.picking',
        'stock_landed_cost_hub_picking_rel',
        'cost_id',
        'picking_id',
        string='Incoming Receipts (Pickings)',
        domain="[('state', '=', 'done')]",
        help='Select the incoming receipts to allocate landed costs to.'
    )
    cost_line_ids = fields.One2many(
        'stock.landed.cost.hub.line',
        'cost_id',
        string='Cost Lines (Charges & Duties)',
        copy=True
    )
    valuation_adjustment_lines = fields.One2many(
        'stock.landed.cost.hub.valuation',
        'cost_id',
        string='Valuation Adjustments',
        readonly=True
    )
    total_cost = fields.Monetary(
        string='Total Landed Cost',
        compute='_compute_total_cost',
        store=True,
        currency_field='currency_id'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('computed', 'Computed'),
        ('posted', 'Posted'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True, readonly=True)

    description = fields.Text(string='Internal Notes')

    @api.depends('cost_line_ids.price_unit')
    def _compute_total_cost(self):
        for record in self:
            record.total_cost = sum(record.cost_line_ids.mapped('price_unit'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.landed.cost.hub') or _('New')
        return super(StockLandedCostHub, self).create(vals_list)

    def action_compute_landed_cost(self):
        """Calculates landed cost distribution across pickings and stock moves."""
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("Please select at least one incoming receipt (picking) before computing."))
        if not self.cost_line_ids:
            raise UserError(_("Please add at least one landed cost line (freight, duty, etc.)."))

        # Clear existing valuation lines
        self.valuation_adjustment_lines.unlink()

        # Collect stock moves from selected pickings
        stock_moves = self.picking_ids.mapped('move_ids').filtered(lambda m: m.state == 'done')
        if not stock_moves:
            raise UserError(_("No completed stock moves found in the selected incoming receipts."))

        val_lines = []
        for cost_line in self.cost_line_ids:
            total_charge = cost_line.price_unit
            if total_charge <= 0:
                continue

            split = cost_line.split_method

            # Compute basis across moves
            move_values = {}
            for move in stock_moves:
                qty = move.quantity or move.product_uom_qty or 1.0
                product = move.product_id

                if split == 'equal':
                    move_values[move] = 1.0
                elif split == 'by_quantity':
                    move_values[move] = qty
                elif split == 'by_weight':
                    weight = product.weight or 1.0
                    move_values[move] = qty * weight
                elif split == 'by_volume':
                    volume = product.volume or 1.0
                    move_values[move] = qty * volume
                elif split == 'by_current_cost_price':
                    cost = product.standard_price or 1.0
                    move_values[move] = qty * cost
                else:
                    move_values[move] = qty

            total_basis = sum(move_values.values()) or 1.0

            for move in stock_moves:
                basis = move_values[move]
                allocated_charge = (basis / total_basis) * total_charge
                qty = move.quantity or move.product_uom_qty or 1.0
                former_cost = move.product_id.standard_price

                val_lines.append((0, 0, {
                    'cost_id': self.id,
                    'cost_line_id': cost_line.id,
                    'stock_move_id': move.id,
                    'product_id': move.product_id.id,
                    'quantity': qty,
                    'former_cost': former_cost,
                    'additional_landed_cost': allocated_charge,
                    'final_unit_cost': former_cost + (allocated_charge / qty if qty else 0.0),
                }))

        self.write({
            'valuation_adjustment_lines': val_lines,
            'state': 'computed'
        })
        return True

    def action_post_landed_cost(self):
        """Posts the landed cost: creates journal entries (if journal set) and updates product cost."""
        self.ensure_one()
        if not self.valuation_adjustment_lines:
            self.action_compute_landed_cost()

        # Update product unit costs
        product_adjustments = {}
        for val in self.valuation_adjustment_lines:
            prod = val.product_id
            if prod not in product_adjustments:
                product_adjustments[prod] = {'qty': 0.0, 'additional_cost': 0.0}
            product_adjustments[prod]['qty'] += val.quantity
            product_adjustments[prod]['additional_cost'] += val.additional_landed_cost

        for prod, data in product_adjustments.items():
            if data['qty'] > 0:
                cost_increase_per_unit = data['additional_cost'] / data['qty']
                prod.sudo().write({
                    'standard_price': prod.standard_price + cost_increase_per_unit
                })

        # Create accounting journal entry if journal is configured
        if self.account_journal_id:
            move_lines = []
            for cost_line in self.cost_line_ids:
                # Credit Landed Cost Clearing / Expense Account
                acc_credit = cost_line.account_id or self.account_journal_id.default_account_id
                if not acc_credit:
                    continue

                move_lines.append((0, 0, {
                    'name': f"{self.name} - {cost_line.product_id.name or 'Landed Cost'}",
                    'account_id': acc_credit.id,
                    'credit': cost_line.price_unit,
                    'debit': 0.0,
                }))

            # Debit Stock Valuation / Interim Account
            total_val = sum(self.valuation_adjustment_lines.mapped('additional_landed_cost'))
            acc_debit = self.account_journal_id.default_account_id
            if acc_debit and total_val > 0:
                move_lines.append((0, 0, {
                    'name': f"{self.name} - Stock Valuation Adjustment",
                    'account_id': acc_debit.id,
                    'debit': total_val,
                    'credit': 0.0,
                }))

            if move_lines:
                try:
                    move = self.env['account.move'].create({
                        'journal_id': self.account_journal_id.id,
                        'date': self.date,
                        'ref': self.name,
                        'line_ids': move_lines,
                    })
                    self.account_move_id = move.id
                except Exception:
                    pass

        self.state = 'posted'
        return True

    def action_cancel(self):
        self.ensure_one()
        self.state = 'cancel'
        return True

    def action_draft(self):
        self.ensure_one()
        self.state = 'draft'
        return True


class StockLandedCostHubLine(models.Model):
    _name = 'stock.landed.cost.hub.line'
    _description = 'Landed Cost Line'

    cost_id = fields.Many2one(
        'stock.landed.cost.hub',
        string='Landed Cost',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Cost Item (Charge / Duty)',
        required=True,
        domain="[('type', '=', 'service')]",
        help='Landed cost service item e.g. Sea Freight, Customs Duty, Terminal Handling.'
    )
    name = fields.Char(string='Description')
    split_method = fields.Selection(
        selection=SPLIT_METHODS,
        string='Split Method',
        required=True,
        default='by_current_cost_price'
    )
    account_id = fields.Many2one(
        'account.account',
        string='Clearing / Expense Account',
        help='Account credited for this landed cost.'
    )
    vendor_bill_id = fields.Many2one(
        'account.move',
        string='Vendor Bill',
        domain="[('move_type', '=', 'in_invoice')]",
        help='Optional link to vendor invoice from carrier or customs broker.'
    )
    foreign_currency_id = fields.Many2one(
        'res.currency',
        string='Foreign Currency',
        help='Currency of the freight or customs charge.'
    )
    foreign_amount = fields.Float(
        string='Foreign Amount',
        default=0.0
    )
    exchange_rate = fields.Float(
        string='Exchange Rate',
        default=1.0,
        digits=(12, 6),
        help='Rate to convert foreign currency into company currency.'
    )
    price_unit = fields.Monetary(
        string='Cost (Company Currency)',
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='cost_id.currency_id',
        string='Company Currency',
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.name
            if hasattr(self.product_id, 'property_account_expense_id') and self.product_id.property_account_expense_id:
                self.account_id = self.product_id.property_account_expense_id.id

    @api.onchange('foreign_amount', 'exchange_rate', 'foreign_currency_id')
    def _onchange_foreign_conversion(self):
        if self.foreign_currency_id and self.foreign_amount:
            rate = self.exchange_rate if self.exchange_rate > 0 else 1.0
            self.price_unit = self.foreign_amount * rate


class StockLandedCostHubValuation(models.Model):
    _name = 'stock.landed.cost.hub.valuation'
    _description = 'Landed Cost Valuation Adjustment Line'
    _order = 'product_id'

    cost_id = fields.Many2one(
        'stock.landed.cost.hub',
        string='Landed Cost',
        required=True,
        ondelete='cascade'
    )
    cost_line_id = fields.Many2one(
        'stock.landed.cost.hub.line',
        string='Cost Line',
        required=True,
        ondelete='cascade'
    )
    stock_move_id = fields.Many2one(
        'stock.move',
        string='Stock Move',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    quantity = fields.Float(string='Quantity', default=1.0)
    former_cost = fields.Monetary(string='Original Unit Cost', currency_field='currency_id')
    additional_landed_cost = fields.Monetary(string='Added Landed Cost', currency_field='currency_id')
    final_unit_cost = fields.Monetary(string='New Unit Cost', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='cost_id.currency_id')
