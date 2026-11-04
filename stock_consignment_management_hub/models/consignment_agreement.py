# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ConsignmentAgreement(models.Model):
    _name = 'consignment.agreement'
    _description = 'Consignment Stock Agreement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Agreement Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Consignment Partner',
        required=True,
        tracking=True
    )
    consignment_type = fields.Selection([
        ('vendor', 'Vendor Consignment (Inward - Supplier Owned in Our Warehouse)'),
        ('customer', 'Customer Consignment (Outward - Our Stock at Customer Site)'),
    ], string='Consignment Type', default='vendor', required=True, tracking=True)

    location_id = fields.Many2one(
        'stock.location',
        string='Consignment Stock Location',
        required=True,
        tracking=True,
        help='Physical or internal location designated for consigned inventory.'
    )
    date_start = fields.Date(
        string='Effective Start Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    date_end = fields.Date(
        string='Expiration Date',
        tracking=True
    )
    billing_frequency = fields.Selection([
        ('daily', 'Daily Consumption Settlement'),
        ('weekly', 'Weekly Consumption Settlement'),
        ('monthly', 'Monthly Consumption Settlement'),
        ('on_demand', 'On-Demand / Manual Settlement'),
    ], string='Billing Frequency', default='monthly', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft Agreement'),
        ('active', 'Active & Operational'),
        ('suspended', 'Suspended'),
        ('closed', 'Closed & Settled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Settlement Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    line_ids = fields.One2many(
        'consignment.agreement.line',
        'agreement_id',
        string='Consigned Products & Price Agreements',
        copy=True
    )
    settlement_ids = fields.One2many(
        'consignment.settlement',
        'agreement_id',
        string='Settlement Batches'
    )
    settlement_count = fields.Integer(
        string='Total Settlements',
        compute='_compute_settlement_count'
    )
    total_active_stock_qty = fields.Float(
        string='On-Hand Consigned Units',
        compute='_compute_stock_aggregates'
    )
    total_active_stock_value = fields.Monetary(
        string='Total Consigned Stock Value',
        currency_field='currency_id',
        compute='_compute_stock_aggregates'
    )
    terms_conditions = fields.Text(string='Consignment Terms & Title Retention Clause')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('consignment.agreement') or _('New')
                vals['name'] = seq
        return super().create(vals_list)

    @api.depends('settlement_ids')
    def _compute_settlement_count(self):
        for rec in self:
            rec.settlement_count = len(rec.settlement_ids)

    @api.depends('line_ids.current_stock_qty', 'line_ids.unit_price')
    def _compute_stock_aggregates(self):
        for rec in self:
            qty = sum(rec.line_ids.mapped('current_stock_qty'))
            val = sum(l.current_stock_qty * l.unit_price for l in rec.line_ids)
            rec.total_active_stock_qty = qty
            rec.total_active_stock_value = val

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise ValidationError(_("Start Date cannot be later than Expiration Date."))

    def action_activate(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Please add at least one consigned product line before activating."))
            rec.state = 'active'

    def action_suspend(self):
        for rec in self:
            rec.state = 'suspended'

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_view_settlements(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("stock_consignment_management_hub.action_consignment_settlement")
        action['domain'] = [('agreement_id', '=', self.id)]
        action['context'] = {'default_agreement_id': self.id, 'default_partner_id': self.partner_id.id}
        return action

    def action_create_settlement(self):
        self.ensure_one()
        settlement = self.env['consignment.settlement'].create({
            'agreement_id': self.id,
            'partner_id': self.partner_id.id,
            'consignment_type': self.consignment_type,
            'company_id': self.company_id.id,
            'currency_id': self.currency_id.id,
        })
        settlement.action_detect_consumption()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'consignment.settlement',
            'res_id': settlement.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_print_statement(self):
        self.ensure_one()
        return self.env.ref('stock_consignment_management_hub.action_report_consignment_statement').report_action(self)


class ConsignmentAgreementLine(models.Model):
    _name = 'consignment.agreement.line'
    _description = 'Consignment Agreement Line'
    _order = 'id'

    agreement_id = fields.Many2one(
        'consignment.agreement',
        string='Agreement',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Consigned Product',
        required=True
    )
    unit_price = fields.Float(
        string='Agreed Settlement Price',
        required=True,
        default=0.0
    )
    commission_rate = fields.Float(
        string='Partner Commission (%)',
        default=0.0
    )
    max_stock_limit = fields.Float(
        string='Max Float Limit',
        default=100.0,
        help='Maximum buffer quantity of consigned stock permitted at location.'
    )
    current_stock_qty = fields.Float(
        string='On-Hand Stock Qty',
        compute='_compute_quantities'
    )
    total_consumed_qty = fields.Float(
        string='Total Consumed Units',
        compute='_compute_quantities'
    )
    unbilled_consumed_qty = fields.Float(
        string='Unbilled Consumed Units',
        compute='_compute_quantities'
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='agreement_id.currency_id',
        readonly=True
    )

    def _compute_quantities(self):
        Quant = self.env['stock.quant']
        MoveLine = self.env['stock.move.line']
        for line in self:
            loc = line.agreement_id.location_id
            if loc and line.product_id:
                # 1. On Hand in consignment location
                quants = Quant.search([
                    ('location_id', '=', loc.id),
                    ('product_id', '=', line.product_id.id),
                ])
                line.current_stock_qty = sum(quants.mapped('quantity'))

                # 2. Consumed moves leaving consignment location
                out_moves = MoveLine.search([
                    ('location_id', '=', loc.id),
                    ('location_dest_id', '!=', loc.id),
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                ])
                consumed = sum(out_moves.mapped('quantity'))
                line.total_consumed_qty = consumed

                # 3. Already settled moves
                settled_lines = self.env['consignment.settlement.line'].search([
                    ('settlement_id.agreement_id', '=', line.agreement_id.id),
                    ('settlement_id.state', 'in', ['invoiced', 'paid']),
                    ('product_id', '=', line.product_id.id),
                ])
                settled = sum(settled_lines.mapped('consumed_qty'))
                line.unbilled_consumed_qty = max(0.0, consumed - settled)
            else:
                line.current_stock_qty = 0.0
                line.total_consumed_qty = 0.0
                line.unbilled_consumed_qty = 0.0
