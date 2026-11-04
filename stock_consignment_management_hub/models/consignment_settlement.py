# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ConsignmentSettlement(models.Model):
    _name = 'consignment.settlement'
    _description = 'Consignment Consumption Settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Settlement Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    agreement_id = fields.Many2one(
        'consignment.agreement',
        string='Consignment Agreement',
        required=True,
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        related='agreement_id.partner_id',
        store=True,
        readonly=True
    )
    consignment_type = fields.Selection(
        related='agreement_id.consignment_type',
        string='Consignment Direction',
        store=True,
        readonly=True
    )
    date = fields.Date(
        string='Settlement Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    period_start = fields.Date(string='Billing Horizon Start')
    period_end = fields.Date(string='Billing Horizon End', default=fields.Date.context_today)

    state = fields.Selection([
        ('draft', 'Draft Work-in-Progress'),
        ('confirmed', 'Consumption Confirmed'),
        ('invoiced', 'Billed / Invoiced'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='agreement_id.company_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='agreement_id.currency_id',
        store=True,
        readonly=True
    )
    line_ids = fields.One2many(
        'consignment.settlement.line',
        'settlement_id',
        string='Settlement Breakdown Lines',
        copy=True
    )
    total_consumed_qty = fields.Float(
        string='Total Units Consumed',
        compute='_compute_totals',
        store=True
    )
    total_settlement_amount = fields.Monetary(
        string='Gross Settlement Total',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    total_commission_amount = fields.Monetary(
        string='Total Commission',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )
    net_settlement_amount = fields.Monetary(
        string='Net Payable / Receivable',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True
    )

    invoice_id = fields.Many2one(
        'account.move',
        string='Generated Bill / Invoice',
        readonly=True,
        copy=False,
        tracking=True
    )
    notes = fields.Text(string='Settlement Notes & Audit Log')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('consignment.settlement') or _('New')
                vals['name'] = seq
        return super().create(vals_list)

    @api.depends('line_ids.consumed_qty', 'line_ids.subtotal', 'line_ids.commission_amount')
    def _compute_totals(self):
        for rec in self:
            rec.total_consumed_qty = sum(rec.line_ids.mapped('consumed_qty'))
            rec.total_settlement_amount = sum(rec.line_ids.mapped('subtotal'))
            rec.total_commission_amount = sum(rec.line_ids.mapped('commission_amount'))
            if rec.consignment_type == 'vendor':
                # Vendor consignment: we owe vendor gross minus our commission
                rec.net_settlement_amount = rec.total_settlement_amount - rec.total_commission_amount
            else:
                # Customer consignment: customer owes us net of their commission
                rec.net_settlement_amount = rec.total_settlement_amount - rec.total_commission_amount

    def action_detect_consumption(self):
        for rec in self:
            rec.line_ids.unlink()
            lines = []
            for agr_line in rec.agreement_id.line_ids:
                agr_line._compute_quantities()
                unbilled = agr_line.unbilled_consumed_qty
                if unbilled > 0:
                    comm = (agr_line.unit_price * unbilled * agr_line.commission_rate) / 100.0
                    lines.append((0, 0, {
                        'product_id': agr_line.product_id.id,
                        'consumed_qty': unbilled,
                        'unit_price': agr_line.unit_price,
                        'commission_rate': agr_line.commission_rate,
                        'commission_amount': comm,
                        'subtotal': unbilled * agr_line.unit_price,
                    }))
            if not lines:
                # If no auto consumption detected, populate agreement products with 0 for manual entry
                for agr_line in rec.agreement_id.line_ids:
                    lines.append((0, 0, {
                        'product_id': agr_line.product_id.id,
                        'consumed_qty': 0.0,
                        'unit_price': agr_line.unit_price,
                        'commission_rate': agr_line.commission_rate,
                        'commission_amount': 0.0,
                        'subtotal': 0.0,
                    }))
            rec.line_ids = lines

    def action_confirm(self):
        for rec in self:
            if not rec.line_ids or sum(rec.line_ids.mapped('consumed_qty')) <= 0:
                raise UserError(_("Cannot confirm settlement with zero consumed units."))
            rec.state = 'confirmed'

    def action_generate_invoice(self):
        for rec in self:
            if rec.state != 'confirmed':
                raise UserError(_("Please confirm consumption before generating invoice/bill."))
            if rec.invoice_id:
                raise UserError(_("An invoice or bill has already been created for this settlement."))

            # Determine invoice type
            move_type = 'in_invoice' if rec.consignment_type == 'vendor' else 'out_invoice'

            # Build invoice lines
            invoice_lines = []
            for line in rec.line_ids.filtered(lambda l: l.consumed_qty > 0):
                invoice_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.consumed_qty,
                    'price_unit': line.unit_price,
                    'name': f"Consignment Consumption: {line.product_id.display_name} ({rec.name})",
                }))

            if not invoice_lines:
                raise UserError(_("No lines with positive consumed quantities to invoice."))

            move_vals = {
                'move_type': move_type,
                'partner_id': rec.partner_id.id,
                'invoice_date': rec.date,
                'date': rec.date,
                'ref': f"Consignment Settlement: {rec.name}",
                'invoice_line_ids': invoice_lines,
                'company_id': rec.company_id.id,
            }

            move = self.env['account.move'].create(move_vals)
            rec.invoice_id = move.id
            rec.state = 'invoiced'

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice linked."))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_reset_draft(self):
        for rec in self:
            if rec.invoice_id and rec.invoice_id.state != 'draft':
                raise UserError(_("Cannot reset to draft while linked invoice is posted."))
            rec.state = 'draft'


class ConsignmentSettlementLine(models.Model):
    _name = 'consignment.settlement.line'
    _description = 'Consignment Settlement Detail Line'
    _order = 'id'

    settlement_id = fields.Many2one(
        'consignment.settlement',
        string='Settlement',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    consumed_qty = fields.Float(
        string='Units Consumed',
        required=True,
        default=0.0
    )
    unit_price = fields.Float(
        string='Agreed Unit Price',
        required=True,
        default=0.0
    )
    commission_rate = fields.Float(
        string='Commission (%)',
        default=0.0
    )
    commission_amount = fields.Monetary(
        string='Commission Amount',
        currency_field='currency_id',
        compute='_compute_line_amounts',
        store=True
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_line_amounts',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='settlement_id.currency_id',
        readonly=True
    )

    @api.depends('consumed_qty', 'unit_price', 'commission_rate')
    def _compute_line_amounts(self):
        for line in self:
            sub = line.consumed_qty * line.unit_price
            comm = (sub * line.commission_rate) / 100.0 if line.commission_rate else 0.0
            line.subtotal = sub
            line.commission_amount = comm
