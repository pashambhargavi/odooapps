# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class QmsRisk(models.Model):
    _name = 'qms.risk'
    _description = 'Quality Risk Register & FMEA (ISO 9001 Clause 6.1)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'initial_rpn desc, id desc'

    name = fields.Char(
        string='Risk Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    title = fields.Char(string='Failure Mode / Risk Event', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Process Department', tracking=True)
    process_step = fields.Char(string='Process / Manufacturing Stage', tracking=True)
    potential_cause = fields.Text(string='Potential Root Cause Mechanism')
    potential_effect = fields.Text(string='Potential Impact on Product / Customer Quality')

    # Initial FMEA Assessment (S x O x D)
    severity = fields.Integer(string='Initial Severity (1-10)', default=5, tracking=True)
    occurrence = fields.Integer(string='Initial Occurrence (1-10)', default=5, tracking=True)
    detection = fields.Integer(string='Initial Detection (1-10)', default=5, tracking=True)
    initial_rpn = fields.Integer(string='Initial RPN Score', compute='_compute_rpn', store=True)

    # Mitigation Plan
    mitigation_action = fields.Text(string='Recommended Mitigation & Error-Proofing (Poka-Yoke)', tracking=True)
    revised_severity = fields.Integer(string='Revised Severity (1-10)', default=2, tracking=True)
    revised_occurrence = fields.Integer(string='Revised Occurrence (1-10)', default=2, tracking=True)
    revised_detection = fields.Integer(string='Revised Detection (1-10)', default=2, tracking=True)
    residual_rpn = fields.Integer(string='Residual RPN Score', compute='_compute_rpn', store=True)
    rpn_reduction_pct = fields.Float(string='Risk Reduction %', compute='_compute_rpn', store=True)

    risk_level = fields.Selection([
        ('low', 'Low Risk (RPN < 50)'),
        ('medium', 'Medium Risk (RPN 50 - 120)'),
        ('high', 'High Risk (RPN 121 - 250)'),
        ('critical', 'Critical Risk (RPN > 250)'),
    ], string='Risk Classification', compute='_compute_risk_level', store=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Identified / Draft'),
        ('assessed', 'Risk Assessed'),
        ('mitigated', 'Mitigation Verified'),
        ('accepted', 'Residual Risk Accepted'),
        ('closed', 'Closed / Retired'),
    ], string='Status', default='draft', required=True, tracking=True)

    responsible_id = fields.Many2one('res.users', string='Risk Owner', default=lambda self: self.env.user, tracking=True)
    review_date = fields.Date(string='Scheduled Review Date', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qms.risk') or _('New')
        return super().create(vals_list)

    @api.depends('severity', 'occurrence', 'detection',
                 'revised_severity', 'revised_occurrence', 'revised_detection')
    def _compute_rpn(self):
        for record in self:
            init_rpn = (record.severity or 1) * (record.occurrence or 1) * (record.detection or 1)
            res_rpn = (record.revised_severity or 1) * (record.revised_occurrence or 1) * (record.revised_detection or 1)
            record.initial_rpn = init_rpn
            record.residual_rpn = res_rpn
            if init_rpn > 0:
                record.rpn_reduction_pct = round(max(0.0, (init_rpn - res_rpn) / init_rpn * 100.0), 1)
            else:
                record.rpn_reduction_pct = 0.0

    @api.depends('initial_rpn')
    def _compute_risk_level(self):
        for record in self:
            rpn = record.initial_rpn
            if rpn > 250:
                record.risk_level = 'critical'
            elif rpn > 120:
                record.risk_level = 'high'
            elif rpn >= 50:
                record.risk_level = 'medium'
            else:
                record.risk_level = 'low'

    def action_assess(self):
        for record in self:
            record.write({'state': 'assessed'})

    def action_mitigate(self):
        for record in self:
            record.write({'state': 'mitigated'})

    def action_accept(self):
        for record in self:
            record.write({'state': 'accepted'})

    def action_close(self):
        for record in self:
            record.write({'state': 'closed'})
