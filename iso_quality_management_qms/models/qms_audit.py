# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class QmsAudit(models.Model):
    _name = 'qms.audit'
    _description = 'ISO Quality Management System Audit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'audit_date desc, id desc'

    name = fields.Char(
        string='Audit Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    title = fields.Char(string='Audit Scope & Objectives', required=True, tracking=True)
    audit_type = fields.Selection([
        ('internal', 'Internal QMS Process Audit'),
        ('supplier', 'Supplier / Vendor Quality Assessment'),
        ('certification', 'External / Registrar Certification Audit'),
    ], string='Audit Classification', default='internal', required=True, tracking=True)

    standard = fields.Selection([
        ('iso_9001', 'ISO 9001:2015 (Quality Management System)'),
        ('iatf_16949', 'IATF 16949:2016 (Automotive QMS)'),
        ('iso_13485', 'ISO 13485:2016 (Medical Devices)'),
        ('as9100', 'AS9100D (Aviation, Space & Defense)'),
        ('iso_22000', 'ISO 22000:2018 (Food Safety Management)'),
    ], string='Audit Standard Framework', default='iso_9001', required=True, tracking=True)

    lead_auditor_id = fields.Many2one('res.users', string='Lead Auditor', default=lambda self: self.env.user, required=True, tracking=True)
    auditor_ids = fields.Many2many('res.users', 'qms_audit_users_rel', 'audit_id', 'user_id', string='Audit Team Members')
    audit_date = fields.Date(string='Scheduled Audit Date', default=fields.Date.today, required=True, tracking=True)
    completion_date = fields.Date(string='Completion Date', tracking=True)

    department_id = fields.Many2one('hr.department', string='Audited Department', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Audited Supplier / Registrar', tracking=True)

    state = fields.Selection([
        ('draft', 'Planned / Draft'),
        ('in_progress', 'Audit In Progress'),
        ('findings_review', 'Findings & Review'),
        ('closed', 'Closed & Approved'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    line_ids = fields.One2many('qms.audit.line', 'audit_id', string='Audit Checklist & Findings Lines')

    total_findings = fields.Integer(string='Total Evaluated Items', compute='_compute_audit_metrics', store=True)
    major_nc_count = fields.Integer(string='Major Non-Conformances', compute='_compute_audit_metrics', store=True)
    minor_nc_count = fields.Integer(string='Minor Non-Conformances', compute='_compute_audit_metrics', store=True)
    observation_count = fields.Integer(string='Observations (OFI)', compute='_compute_audit_metrics', store=True)

    overall_result = fields.Selection([
        ('passed', 'Fully Conforming (Audit Passed)'),
        ('conditional', 'Conditional Approval (Minor NCs Corrective Action Required)'),
        ('failed', 'Critical Non-Conformance (Audit Failed / Re-Audit Mandatory)'),
    ], string='Overall Audit Conclusion', compute='_compute_audit_metrics', store=True, tracking=True)

    executive_summary = fields.Text(string='Auditor Executive Conclusions & Recommendations')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qms.audit') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids', 'line_ids.result')
    def _compute_audit_metrics(self):
        for record in self:
            total = len(record.line_ids)
            majors = len(record.line_ids.filtered(lambda l: l.result == 'major_nc'))
            minors = len(record.line_ids.filtered(lambda l: l.result == 'minor_nc'))
            obs = len(record.line_ids.filtered(lambda l: l.result == 'observation'))

            record.total_findings = total
            record.major_nc_count = majors
            record.minor_nc_count = minors
            record.observation_count = obs

            if majors > 0:
                record.overall_result = 'failed'
            elif minors > 0:
                record.overall_result = 'conditional'
            else:
                record.overall_result = 'passed'

    def action_start(self):
        for record in self:
            record.write({'state': 'in_progress'})

    def action_review(self):
        for record in self:
            record.write({'state': 'findings_review'})

    def action_close(self):
        for record in self:
            # Check if any major or minor NC has an open NCR
            open_ncs = record.line_ids.filtered(lambda l: l.result in ('major_nc', 'minor_nc') and not l.ncr_id)
            if open_ncs:
                raise UserError(_("Before closing the audit, please generate an official Non-Conformance Report (NCR) for all Major and Minor findings."))
            record.write({
                'state': 'closed',
                'completion_date': fields.Date.today(),
            })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancelled'})

    def action_load_iso9001_template(self):
        self.ensure_one()
        clauses = [
            ("Clause 4.3", "Determining the scope of the quality management system and documented boundaries"),
            ("Clause 5.2", "Quality policy established, implemented and maintained by top management"),
            ("Clause 6.1", "Actions to address risks and opportunities (Risk Register & FMEA evaluations)"),
            ("Clause 7.1.5", "Monitoring and measuring resources: Tool calibration, equipment traceability"),
            ("Clause 7.2", "Competence and training records of personnel performing quality inspections"),
            ("Clause 8.2", "Requirements for products and services: Customer contract and spec review"),
            ("Clause 8.4", "Control of externally provided processes, products and vendor evaluation"),
            ("Clause 8.5.1", "Control of production and service provision under controlled conditions"),
            ("Clause 8.7", "Control of non-conforming outputs, quarantine segregation and disposition"),
            ("Clause 9.2", "Internal audit program implementation, schedule compliance and independence"),
            ("Clause 10.2", "Non-conformity and corrective action (CAPA) implementation and effectiveness"),
        ]
        lines = []
        for cl, req in clauses:
            lines.append((0, 0, {
                'clause': cl,
                'requirement': req,
                'result': 'compliant',
            }))
        self.write({'line_ids': lines})


class QmsAuditLine(models.Model):
    _name = 'qms.audit.line'
    _description = 'ISO Audit Checklist Line & Finding'
    _order = 'clause asc, id asc'

    audit_id = fields.Many2one('qms.audit', string='Audit Session', required=True, ondelete='cascade')
    clause = fields.Char(string='Standard Clause', required=True)
    requirement = fields.Text(string='Requirement Specification', required=True)
    result = fields.Selection([
        ('compliant', 'Compliant / Conforming'),
        ('observation', 'Opportunity for Improvement (OFI)'),
        ('minor_nc', 'Minor Non-Conformance'),
        ('major_nc', 'Major Non-Conformance'),
    ], string='Auditor Finding', default='compliant', required=True)

    evidence = fields.Text(string='Objective Evidence & Sampling Notes')
    ncr_id = fields.Many2one('qms.ncr', string='Triggered NCR')

    def action_generate_ncr(self):
        self.ensure_one()
        if self.ncr_id:
            raise UserError(_("An NCR has already been generated for this audit finding."))
        sev = 'critical' if self.result == 'major_nc' else 'major'
        ncr = self.env['qms.ncr'].create({
            'title': _("Audit NC (%s): %s") % (self.clause, self.audit_id.title),
            'source_type': 'audit',
            'severity': sev,
            'description': _("Audit Finding under %s:\n%s\n\nObjective Evidence:\n%s") % (
                self.clause, self.requirement, self.evidence or _("Observed during audit")
            ),
            'user_id': self.audit_id.lead_auditor_id.id,
            'qa_manager_id': self.audit_id.lead_auditor_id.id,
            'company_id': self.audit_id.company_id.id,
        })
        self.ncr_id = ncr.id
        return {
            'name': _('Non-Conformance Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'qms.ncr',
            'view_mode': 'form',
            'res_id': ncr.id,
            'target': 'current',
        }
