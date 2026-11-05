# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class QmsCapa(models.Model):
    _name = 'qms.capa'
    _description = 'Corrective and Preventive Action (CAPA / 8D)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='CAPA Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    title = fields.Char(
        string='CAPA Title / Subject',
        required=True,
        tracking=True
    )
    capa_type = fields.Selection([
        ('corrective', 'Corrective Action (NCR / Defect Rectification)'),
        ('preventive', 'Preventive Action (Risk Proactive Mitigation)'),
        ('continuous_improvement', 'Continuous Improvement (Kaizen / CI Initiative)'),
    ], string='CAPA Classification', default='corrective', required=True, tracking=True)

    source = fields.Selection([
        ('ncr', 'Non-Conformance Report (NCR)'),
        ('audit', 'Quality Audit Finding'),
        ('customer_complaint', 'Customer Complaint / RMA Return'),
        ('risk_assessment', 'FMEA Risk Register'),
        ('management_review', 'Executive Management Review'),
    ], string='Source of Initiative', default='ncr', required=True, tracking=True)

    ncr_id = fields.Many2one('qms.ncr', string='Originating NCR', tracking=True)
    audit_id = fields.Many2one('qms.audit', string='Originating Audit', tracking=True)
    product_id = fields.Many2one('product.product', string='Product / Part Affected', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer / Vendor Involved', tracking=True)

    # D1: Champion & Cross-Functional Team
    assigned_to_id = fields.Many2one('res.users', string='Lead Investigator', default=lambda self: self.env.user, tracking=True)
    team_leader_id = fields.Many2one('res.users', string='D1 Team Champion', tracking=True)
    team_member_ids = fields.Many2many('res.users', 'qms_capa_users_rel', 'capa_id', 'user_id', string='D1 Cross-Functional Team')

    # D2: Problem Statement
    problem_statement = fields.Text(string='D2 Problem Statement (5W2H)', required=True)
    is_contained = fields.Boolean(string='Defect Contained', default=False)

    # D3: Immediate Containment
    containment_actions = fields.Text(string='D3 Immediate Containment Actions', tracking=True)
    containment_date = fields.Date(string='Containment Date', tracking=True)

    # D4: Root Cause Analysis (5-Whys + Ishikawa 6M)
    why_1 = fields.Char(string='Why 1: Direct Symptom')
    why_2 = fields.Char(string='Why 2: Contributing Cause')
    why_3 = fields.Char(string='Why 3: Process Gap')
    why_4 = fields.Char(string='Why 4: Systemic Failure')
    why_5 = fields.Char(string='Why 5: Fundamental Root Cause')
    root_cause_summary = fields.Text(string='Root Cause Synthesis & Determination', tracking=True)

    ishikawa_man = fields.Text(string='Man (Personnel, Competency, Training)')
    ishikawa_machine = fields.Text(string='Machine (Tooling, Calibration, Maintenance)')
    ishikawa_material = fields.Text(string='Material (Specifications, Subcontractors)')
    ishikawa_method = fields.Text(string='Method (Procedures, SOPs, Work Instructions)')
    ishikawa_measurement = fields.Text(string='Measurement (Gauges, Inspection, Metrology)')
    ishikawa_environment = fields.Text(string='Milieu / Environment (ESD, Temp, Lighting, Dust)')

    # D5: Corrective Actions Plan
    action_line_ids = fields.One2many('qms.capa.action', 'capa_id', string='D5 Corrective Action Lines')
    action_count = fields.Integer(string='Total Actions', compute='_compute_action_counts')
    action_completed_count = fields.Integer(string='Completed Actions', compute='_compute_action_counts')

    # D6: Verification of Effectiveness
    verification_method = fields.Selection([
        ('audit', 'Follow-up Process Audit'),
        ('sampling', 'Extended Statistical Lot Sampling'),
        ('run_chart', 'SPC Run Chart & Capability Analysis (Cpk)'),
        ('zero_defects', 'Zero Recurrence for 30/60 Calendar Days'),
    ], string='D6 Verification Methodology', default='zero_defects', tracking=True)
    verification_result = fields.Text(string='D6 Verification Evidence & Results', tracking=True)
    verified_by_id = fields.Many2one('res.users', string='Verified By (QA Lead)', tracking=True)
    verification_date = fields.Date(string='Verification Date', tracking=True)

    # D7: Prevention of Recurrence & Standardization
    preventive_actions = fields.Text(string='D7 Systemic Preventive Countermeasures', tracking=True)
    sop_updated = fields.Boolean(string='Standard Operating Procedure (SOP) Updated?', default=False)
    sop_reference = fields.Char(string='Updated SOP Reference Number')

    # D8: Team Recognition & Closure
    closure_notes = fields.Text(string='D8 Closure & Team Acknowledgement', tracking=True)
    close_date = fields.Date(string='Formal Closure Date', tracking=True)

    # FMEA Risk Priority Numbers (RPN)
    initial_severity = fields.Integer(string='Initial Severity (1-10)', default=5)
    initial_occurrence = fields.Integer(string='Initial Occurrence (1-10)', default=5)
    initial_detection = fields.Integer(string='Initial Detection (1-10)', default=5)
    initial_rpn = fields.Integer(string='Initial RPN', compute='_compute_rpn', store=True)

    residual_severity = fields.Integer(string='Residual Severity (1-10)', default=2)
    residual_occurrence = fields.Integer(string='Residual Occurrence (1-10)', default=2)
    residual_detection = fields.Integer(string='Residual Detection (1-10)', default=2)
    residual_rpn = fields.Integer(string='Residual RPN', compute='_compute_rpn', store=True)
    rpn_reduction_pct = fields.Float(string='RPN Risk Reduction (%)', compute='_compute_rpn', store=True)

    state = fields.Selection([
        ('d1_team', 'D1: Team Assembly'),
        ('d2_problem', 'D2: Problem Definition'),
        ('d3_containment', 'D3: Containment'),
        ('d4_root_cause', 'D4: Root Cause Analysis'),
        ('d5_actions', 'D5: Corrective Actions'),
        ('d6_verification', 'D6: Verification'),
        ('d7_prevention', 'D7: Systemic Prevention'),
        ('d8_closed', 'D8: Closed & Recognized'),
        ('cancelled', 'Cancelled'),
    ], string='8D Stage', default='d1_team', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qms.capa') or _('New')
        return super().create(vals_list)

    @api.depends('initial_severity', 'initial_occurrence', 'initial_detection',
                 'residual_severity', 'residual_occurrence', 'residual_detection')
    def _compute_rpn(self):
        for record in self:
            init_rpn = (record.initial_severity or 1) * (record.initial_occurrence or 1) * (record.initial_detection or 1)
            res_rpn = (record.residual_severity or 1) * (record.residual_occurrence or 1) * (record.residual_detection or 1)
            record.initial_rpn = init_rpn
            record.residual_rpn = res_rpn
            if init_rpn > 0:
                record.rpn_reduction_pct = round(max(0.0, (init_rpn - res_rpn) / init_rpn * 100.0), 1)
            else:
                record.rpn_reduction_pct = 0.0

    @api.depends('action_line_ids', 'action_line_ids.state')
    def _compute_action_counts(self):
        for record in self:
            record.action_count = len(record.action_line_ids)
            record.action_completed_count = len(record.action_line_ids.filtered(lambda a: a.state in ('completed', 'verified')))

    def action_advance_stage(self):
        stage_order = ['d1_team', 'd2_problem', 'd3_containment', 'd4_root_cause', 'd5_actions', 'd6_verification', 'd7_prevention', 'd8_closed']
        for record in self:
            if record.state in stage_order:
                current_idx = stage_order.index(record.state)
                if current_idx < len(stage_order) - 1:
                    next_stage = stage_order[current_idx + 1]
                    # Validation rules
                    if record.state == 'd3_containment' and not record.containment_actions:
                        raise UserError(_("Please document D3 Immediate Containment Actions before proceeding to Root Cause Analysis."))
                    if record.state == 'd4_root_cause' and not record.root_cause_summary:
                        raise UserError(_("Please document the Root Cause Determination (D4) before formulating corrective actions."))
                    if record.state == 'd5_actions':
                        if not record.action_line_ids:
                            raise UserError(_("Please define at least one Corrective Action Plan line in D5 before advancing to Verification."))
                        pending = record.action_line_ids.filtered(lambda a: a.state not in ('completed', 'verified'))
                        if pending:
                            raise UserError(_("All D5 Corrective Actions must be marked as Completed or Verified before proceeding to D6 Verification."))
                    if next_stage == 'd8_closed':
                        record.close_date = fields.Date.today()
                        if record.ncr_id and record.ncr_id.state == 'capa_required':
                            record.ncr_id.write({'state': 'closed', 'close_date': fields.Date.today()})
                    record.write({'state': next_stage})

    def action_close_capa(self):
        for record in self:
            if not record.verification_result:
                raise UserError(_("Please document the D6 Verification Evidence and Effectiveness results before closing the CAPA."))
            record.write({
                'state': 'd8_closed',
                'close_date': fields.Date.today(),
            })
            if record.ncr_id and record.ncr_id.state == 'capa_required':
                record.ncr_id.write({'state': 'closed', 'close_date': fields.Date.today()})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancelled'})
