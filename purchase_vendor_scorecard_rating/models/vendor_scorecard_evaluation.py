# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VendorScorecardEvaluation(models.Model):
    _name = 'vendor.scorecard.evaluation'
    _description = 'Vendor Performance Evaluation & Scorecard'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'final_score desc, id desc'

    name = fields.Char(string='Scorecard Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor / Supplier',
        required=True,
        domain="['|', ('supplier_rank', '>', 0), ('is_company', '=', True)]",
        tracking=True
    )
    period_id = fields.Many2one(
        'vendor.scorecard.period',
        string='Evaluation Period',
        required=True,
        ondelete='cascade',
        tracking=True
    )
    template_id = fields.Many2one(
        'vendor.scorecard.template',
        string='Scoring Template',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='period_id.company_id',
        store=True,
        readonly=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft Work-in-Progress'),
        ('reviewed', 'QA / Procurement Reviewed'),
        ('approved', 'Management Approved'),
        ('published', 'Published & Active'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    evaluator_id = fields.Many2one(
        'res.users',
        string='Lead Evaluator',
        default=lambda self: self.env.user,
        tracking=True
    )
    evaluation_date = fields.Date(string='Evaluation Date', default=fields.Date.context_today)

    # Statistical Aggregates
    total_orders_count = fields.Integer(string='Purchase Orders Placed', readonly=True)
    total_amount_purchased = fields.Monetary(string='Total Spend Volume', currency_field='currency_id', readonly=True)
    total_pickings_count = fields.Integer(string='Receipt Shipments', readonly=True)
    ontime_pickings_count = fields.Integer(string='On-Time Shipments', readonly=True)
    late_pickings_count = fields.Integer(string='Late Shipments', readonly=True)

    total_qty_ordered = fields.Float(string='Total Units Ordered', readonly=True)
    total_qty_delivered = fields.Float(string='Total Units Received', readonly=True)
    total_qty_returned = fields.Float(string='Total Units Returned / Defective', readonly=True)

    # Core Calculated Percentages
    otd_rate = fields.Float(string='On-Time Delivery Rate (%)', readonly=True)
    fulfillment_rate = fields.Float(string='Quantity Fill Rate (%)', readonly=True)
    quality_rate = fields.Float(string='Quality Acceptance Rate (%)', readonly=True)
    price_variance_rate = fields.Float(string='Price Stability Rate (%)', readonly=True)
    service_score = fields.Float(string='Service & Responsiveness (0-100)', default=90.0, tracking=True)

    # Evaluation Lines
    line_ids = fields.One2many(
        'vendor.scorecard.evaluation.line',
        'evaluation_id',
        string='Evaluation Breakdown',
        copy=True
    )

    # Overall Score & Tier
    final_score = fields.Float(string='Final Performance Score (%)', compute='_compute_final_score', store=True, tracking=True)
    grade = fields.Selection([
        ('grade_a', 'Grade A - Preferred Partner'),
        ('grade_b', 'Grade B - Approved Supplier'),
        ('grade_c', 'Grade C - Conditional / Warning'),
        ('grade_d', 'Grade D - Blacklisted / Restricted'),
    ], string='Supplier Grade', compute='_compute_grade', store=True, tracking=True)

    grade_badge_color = fields.Char(string='Badge Color', compute='_compute_badge_color')

    notes = fields.Text(string='Auditor Assessment & Notes')
    corrective_action_plan = fields.Text(string='Corrective Action & Improvement Plan (CAPA)')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                partner_id = vals.get('partner_id')
                partner_name = self.env['res.partner'].browse(partner_id).name if partner_id else 'Vendor'
                vals['name'] = f"VSC/{fields.Date.today().year}/{partner_name[:12].strip()}"
        return super().create(vals_list)

    @api.depends('line_ids.weighted_score', 'template_id.total_weight')
    def _compute_final_score(self):
        for rec in self:
            total_weight = rec.template_id.total_weight or sum(rec.line_ids.mapped('weight')) or 100.0
            sum_weighted = sum(rec.line_ids.mapped('weighted_score'))
            rec.final_score = round((sum_weighted / total_weight) * 100.0, 2) if total_weight > 0 else 0.0

    @api.depends('final_score', 'template_id')
    def _compute_grade(self):
        for rec in self:
            tmpl = rec.template_id
            score = rec.final_score
            min_a = tmpl.min_grade_a if tmpl else 90.0
            min_b = tmpl.min_grade_b if tmpl else 75.0
            min_c = tmpl.min_grade_c if tmpl else 60.0

            if score >= min_a:
                rec.grade = 'grade_a'
            elif score >= min_b:
                rec.grade = 'grade_b'
            elif score >= min_c:
                rec.grade = 'grade_c'
            else:
                rec.grade = 'grade_d'

    @api.depends('grade')
    def _compute_badge_color(self):
        for rec in self:
            if rec.grade == 'grade_a':
                rec.grade_badge_color = '#10b981'  # Emerald green
            elif rec.grade == 'grade_b':
                rec.grade_badge_color = '#0284c7'  # Sky blue
            elif rec.grade == 'grade_c':
                rec.grade_badge_color = '#f59e0b'  # Amber
            else:
                rec.grade_badge_color = '#ef4444'  # Rose red

    def action_compute_metrics(self):
        for rec in self:
            if not rec.template_id:
                raise UserError(_("Please assign a Scoring Template to evaluate."))

            start_dt = datetime.combine(rec.period_id.date_from, time.min)
            end_dt = datetime.combine(rec.period_id.date_to, time.max)

            # 1. Purchase Orders
            PO = rec.env['purchase.order']
            orders = PO.search([
                ('partner_id', '=', rec.partner_id.id),
                ('date_approve', '>=', start_dt),
                ('date_approve', '<=', end_dt),
                ('state', 'in', ['purchase', 'done']),
                ('company_id', '=', rec.company_id.id),
            ])
            rec.total_orders_count = len(orders)
            rec.total_amount_purchased = sum(orders.mapped('amount_total'))

            # 2. Stock Pickings (Receipts)
            Picking = rec.env['stock.picking']
            pickings = Picking.search([
                ('partner_id', '=', rec.partner_id.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('date_done', '>=', start_dt),
                ('date_done', '<=', end_dt),
                ('state', '=', 'done'),
                ('company_id', '=', rec.company_id.id),
            ])
            rec.total_pickings_count = len(pickings)
            ontime = 0
            late = 0
            for p in pickings:
                # Compare date_done with scheduled_date
                if p.scheduled_date and p.date_done:
                    if p.date_done.date() <= p.scheduled_date.date():
                        ontime += 1
                    else:
                        late += 1
                else:
                    ontime += 1

            rec.ontime_pickings_count = ontime
            rec.late_pickings_count = late
            rec.otd_rate = round((ontime / len(pickings) * 100.0), 2) if pickings else 100.0

            # 3. Quantities & Fulfillment
            lines = rec.env['purchase.order.line'].search([('order_id', 'in', orders.ids)])
            rec.total_qty_ordered = sum(lines.mapped('product_qty'))
            rec.total_qty_delivered = sum(lines.mapped('qty_received'))
            rec.fulfillment_rate = round(min(100.0, (rec.total_qty_delivered / rec.total_qty_ordered * 100.0)), 2) if rec.total_qty_ordered else 100.0

            # 4. Returns & Defect Rate
            returns = Picking.search([
                ('partner_id', '=', rec.partner_id.id),
                ('picking_type_id.code', '=', 'outgoing'),
                ('origin', 'ilike', 'Return'),
                ('date_done', '>=', start_dt),
                ('date_done', '<=', end_dt),
                ('state', '=', 'done'),
                ('company_id', '=', rec.company_id.id),
            ])
            # In Odoo 19, move_ids has quantity
            qty_ret = 0.0
            for ret in returns:
                qty_ret += sum(ret.move_ids.mapped('quantity'))
            rec.total_qty_returned = qty_ret
            if rec.total_qty_delivered > 0:
                defect_pct = (qty_ret / rec.total_qty_delivered) * 100.0
                rec.quality_rate = round(max(0.0, 100.0 - defect_pct), 2)
            else:
                rec.quality_rate = 100.0

            # 5. Price Stability Rate
            rec.price_variance_rate = 100.0  # Baseline 100% adherence

            # 6. Build or update line items based on criteria
            rec.line_ids.unlink()
            line_vals = []
            for crit in rec.template_id.criterion_ids:
                actual = 0.0
                if crit.metric_type == 'otd':
                    actual = rec.otd_rate
                elif crit.metric_type == 'fulfillment':
                    actual = rec.fulfillment_rate
                elif crit.metric_type == 'quality':
                    actual = rec.quality_rate
                elif crit.metric_type == 'price':
                    actual = rec.price_variance_rate
                elif crit.metric_type == 'service':
                    actual = rec.service_score

                # Compute line score relative to target (capped at 100%)
                target = crit.benchmark_target or 100.0
                score = min(100.0, max(0.0, (actual / target) * 100.0)) if target > 0 else 0.0
                weighted = (score * crit.weight) / 100.0

                line_vals.append((0, 0, {
                    'criterion_id': crit.id,
                    'name': crit.name,
                    'metric_type': crit.metric_type,
                    'weight': crit.weight,
                    'benchmark_target': crit.benchmark_target,
                    'actual_value': actual,
                    'score': round(score, 2),
                    'weighted_score': round(weighted, 2),
                }))

            rec.line_ids = line_vals
            rec._compute_final_score()
            rec._compute_grade()

    def action_review(self):
        for rec in self:
            rec.state = 'reviewed'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def action_publish(self):
        for rec in self:
            rec.state = 'published'
            # Update partner record with current grade
            rec.partner_id.write({
                'latest_scorecard_id': rec.id,
                'supplier_grade': rec.grade,
                'supplier_score': rec.final_score,
            })

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_print_scorecard_report(self):
        self.ensure_one()
        return self.env.ref('purchase_vendor_scorecard_rating.action_report_vendor_scorecard').report_action(self)


class VendorScorecardEvaluationLine(models.Model):
    _name = 'vendor.scorecard.evaluation.line'
    _description = 'Vendor Scorecard Evaluation Line'
    _order = 'id'

    evaluation_id = fields.Many2one(
        'vendor.scorecard.evaluation',
        string='Evaluation',
        ondelete='cascade',
        required=True
    )
    criterion_id = fields.Many2one(
        'vendor.scorecard.criterion',
        string='Criterion',
        ondelete='set null'
    )
    name = fields.Char(string='Criterion Name', required=True)
    metric_type = fields.Selection([
        ('otd', 'On-Time Delivery Rate (OTD %)'),
        ('fulfillment', 'Quantity Fulfillment Fill Rate (%)'),
        ('quality', 'Quality Acceptance Rate (%)'),
        ('price', 'Price Variance & Stability (%)'),
        ('service', 'Service, Responsiveness & Support (Qualitative)'),
    ], string='Metric Type', required=True)

    weight = fields.Float(string='Weight (%)', required=True)
    benchmark_target = fields.Float(string='Benchmark Target (%)', default=95.0)
    actual_value = fields.Float(string='Actual Performance (%)', default=0.0)
    score = fields.Float(string='Normalized Score (0-100)', default=0.0)
    weighted_score = fields.Float(string='Weighted Points', default=0.0)

    @api.onchange('actual_value', 'weight', 'benchmark_target')
    def _onchange_actual_value(self):
        target = self.benchmark_target or 100.0
        self.score = min(100.0, max(0.0, (self.actual_value / target) * 100.0)) if target > 0 else 0.0
        self.weighted_score = (self.score * self.weight) / 100.0
