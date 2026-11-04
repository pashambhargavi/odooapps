# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ConsignmentAudit(models.Model):
    _name = 'consignment.audit'
    _description = 'Consignment Physical Stock Audit & Reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc, id desc'

    name = fields.Char(
        string='Audit Reference',
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
        related='agreement_id.partner_id',
        string='Partner',
        store=True,
        readonly=True
    )
    audit_date = fields.Date(
        string='Audit Date',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    auditor_id = fields.Many2one(
        'res.users',
        string='Stock Auditor',
        default=lambda self: self.env.user,
        tracking=True
    )
    state = fields.Selection([
        ('draft', 'Draft Audit'),
        ('in_progress', 'Counting In Progress'),
        ('reconciled', 'Reconciled & Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    company_id = fields.Many2one(
        'res.company',
        related='agreement_id.company_id',
        string='Company',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='agreement_id.currency_id',
        string='Currency',
        store=True,
        readonly=True
    )
    line_ids = fields.One2many(
        'consignment.audit.line',
        'audit_id',
        string='Physical Count Items',
        copy=True
    )
    total_theoretical_qty = fields.Float(
        string='Theoretical Book Units',
        compute='_compute_audit_totals',
        store=True
    )
    total_physical_qty = fields.Float(
        string='Physical Counted Units',
        compute='_compute_audit_totals',
        store=True
    )
    total_variance_qty = fields.Float(
        string='Total Discrepancy Units',
        compute='_compute_audit_totals',
        store=True
    )
    total_variance_value = fields.Monetary(
        string='Discrepancy Valuation',
        currency_field='currency_id',
        compute='_compute_audit_totals',
        store=True
    )
    notes = fields.Text(string='Auditor Comments & Root Cause Analysis')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('consignment.audit') or _('New')
                vals['name'] = seq
        return super().create(vals_list)

    @api.depends('line_ids.theoretical_qty', 'line_ids.physical_qty', 'line_ids.variance_qty', 'line_ids.variance_value')
    def _compute_audit_totals(self):
        for rec in self:
            rec.total_theoretical_qty = sum(rec.line_ids.mapped('theoretical_qty'))
            rec.total_physical_qty = sum(rec.line_ids.mapped('physical_qty'))
            rec.total_variance_qty = sum(rec.line_ids.mapped('variance_qty'))
            rec.total_variance_value = sum(rec.line_ids.mapped('variance_value'))

    def action_start_count(self):
        for rec in self:
            rec.line_ids.unlink()
            lines = []
            for agr_line in rec.agreement_id.line_ids:
                agr_line._compute_quantities()
                lines.append((0, 0, {
                    'product_id': agr_line.product_id.id,
                    'theoretical_qty': agr_line.current_stock_qty,
                    'physical_qty': agr_line.current_stock_qty,
                    'unit_price': agr_line.unit_price,
                }))
            rec.line_ids = lines
            rec.state = 'in_progress'

    def action_reconcile(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("No physical count items to reconcile."))
            rec.state = 'reconciled'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'


class ConsignmentAuditLine(models.Model):
    _name = 'consignment.audit.line'
    _description = 'Consignment Physical Count Item'
    _order = 'id'

    audit_id = fields.Many2one(
        'consignment.audit',
        string='Audit',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )
    theoretical_qty = fields.Float(
        string='Theoretical Book Qty',
        readonly=True,
        default=0.0
    )
    physical_qty = fields.Float(
        string='Physical Counted Qty',
        required=True,
        default=0.0
    )
    variance_qty = fields.Float(
        string='Discrepancy (Units)',
        compute='_compute_variance',
        store=True
    )
    unit_price = fields.Float(
        string='Valuation Price',
        required=True,
        default=0.0
    )
    variance_value = fields.Monetary(
        string='Discrepancy Value',
        currency_field='currency_id',
        compute='_compute_variance',
        store=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='audit_id.currency_id',
        readonly=True
    )

    @api.depends('theoretical_qty', 'physical_qty', 'unit_price')
    def _compute_variance(self):
        for line in self:
            diff = line.physical_qty - line.theoretical_qty
            line.variance_qty = diff
            line.variance_value = diff * line.unit_price
