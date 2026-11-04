# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorScorecardTemplate(models.Model):
    _name = 'vendor.scorecard.template'
    _description = 'Vendor Scorecard Evaluation Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    criterion_ids = fields.One2many(
        'vendor.scorecard.criterion',
        'template_id',
        string='Evaluation Criteria',
        copy=True
    )

    min_grade_a = fields.Float(string='Grade A Minimum Score (%)', default=90.0)
    min_grade_b = fields.Float(string='Grade B Minimum Score (%)', default=75.0)
    min_grade_c = fields.Float(string='Grade C Minimum Score (%)', default=60.0)

    total_weight = fields.Float(
        string='Total Weight (%)',
        compute='_compute_total_weight',
        store=True
    )

    @api.depends('criterion_ids.weight')
    def _compute_total_weight(self):
        for rec in self:
            rec.total_weight = sum(rec.criterion_ids.mapped('weight'))

    @api.constrains('min_grade_a', 'min_grade_b', 'min_grade_c')
    def _check_grade_thresholds(self):
        for rec in self:
            if not (100.0 >= rec.min_grade_a > rec.min_grade_b > rec.min_grade_c >= 0):
                raise ValidationError(_("Grade thresholds must strictly follow: 100 >= Grade A > Grade B > Grade C >= 0."))


class VendorScorecardCriterion(models.Model):
    _name = 'vendor.scorecard.criterion'
    _description = 'Vendor Scorecard Evaluation Criterion'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    template_id = fields.Many2one(
        'vendor.scorecard.template',
        string='Template',
        ondelete='cascade',
        required=True
    )
    name = fields.Char(string='Criterion Name', required=True)
    metric_type = fields.Selection([
        ('otd', 'On-Time Delivery Rate (OTD %)'),
        ('fulfillment', 'Quantity Fulfillment Fill Rate (%)'),
        ('quality', 'Quality Acceptance Rate (%)'),
        ('price', 'Price Variance & Stability (%)'),
        ('service', 'Service, Responsiveness & Support (Qualitative)'),
    ], string='Metric Type', default='otd', required=True)

    weight = fields.Float(string='Weight (%)', default=25.0, required=True)
    benchmark_target = fields.Float(string='Benchmark Target (%)', default=95.0, required=True)
    description = fields.Text(string='Metric Description & Measurement Rules')

    @api.constrains('weight')
    def _check_weight(self):
        for rec in self:
            if rec.weight < 0:
                raise ValidationError(_("Weight cannot be negative."))
