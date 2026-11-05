# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

class TrainingParticipation(models.Model):
    _name = 'training.participation'
    _description = 'Training Record, Evaluation & Certification'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'issue_date desc, id desc'

    name = fields.Char(string='Record Ref', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    certificate_number = fields.Char(string='Certificate Number', copy=False, readonly=True, tracking=True)
    
    session_id = fields.Many2one('training.session', string='Training Session', ondelete='cascade')
    course_id = fields.Many2one('training.course', string='Course', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', string='Department', store=True)
    job_id = fields.Many2one('hr.job', related='employee_id.job_id', string='Job Position', store=True)
    
    attendance_status = fields.Selection([
        ('registered', 'Registered'),
        ('attended', 'Attended'),
        ('absent', 'Absent / No Show'),
        ('excused', 'Excused'),
    ], string='Attendance', default='registered', required=True, tracking=True)
    
    score = fields.Float(string='Score Achieved (%)', default=0.0, tracking=True)
    passing_score = fields.Float(related='course_id.passing_score', string='Passing Score (%)', readonly=True)
    
    evaluation_result = fields.Selection([
        ('pending', 'Pending Evaluation'),
        ('passed', 'Passed & Certified'),
        ('failed', 'Failed (Re-sit Required)'),
    ], string='Result', default='pending', required=True, tracking=True)
    
    issue_date = fields.Date(string='Issue Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', compute='_compute_expiry_date', store=True, tracking=True)
    days_until_expiry = fields.Integer(string='Days to Expiry', compute='_compute_days_until_expiry')
    
    certificate_status = fields.Selection([
        ('draft', 'Draft / Not Issued'),
        ('valid', 'Valid & Certified'),
        ('expiring_soon', 'Expiring Soon (<30 Days)'),
        ('expired', 'Expired (Non-Compliant)'),
        ('revoked', 'Revoked'),
    ], string='Certificate Status', default='draft', required=True, tracking=True, store=True)
    
    evaluator_notes = fields.Text(string='Evaluator Notes / Remarks')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('training.participation') or _('New')
            # If session is provided and course is not, grab from session
            if vals.get('session_id') and not vals.get('course_id'):
                session = self.env['training.session'].browse(vals['session_id'])
                vals['course_id'] = session.course_id.id
            if 'score' in vals and vals.get('course_id'):
                course = self.env['training.course'].browse(vals['course_id'])
                if vals.get('score', 0.0) >= course.passing_score:
                    vals['evaluation_result'] = 'passed'
                elif vals.get('score', 0.0) > 0.0:
                    vals['evaluation_result'] = 'failed'
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if 'score' in vals:
            for rec in self:
                if rec.score >= rec.course_id.passing_score:
                    rec.evaluation_result = 'passed'
                elif rec.score > 0.0:
                    rec.evaluation_result = 'failed'
        return res

    @api.depends('issue_date', 'course_id.validity_months')
    def _compute_expiry_date(self):
        for rec in self:
            if rec.issue_date and rec.course_id and rec.course_id.validity_months > 0:
                rec.expiry_date = rec.issue_date + relativedelta(months=rec.course_id.validity_months)
            else:
                rec.expiry_date = False

    @api.depends('expiry_date')
    def _compute_days_until_expiry(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expiry_date:
                rec.days_until_expiry = (rec.expiry_date - today).days
            else:
                rec.days_until_expiry = 9999

    @api.onchange('score')
    def _onchange_score(self):
        if self.score and self.course_id:
            if self.score >= self.course_id.passing_score:
                self.evaluation_result = 'passed'
            else:
                self.evaluation_result = 'failed'

    def action_issue_certificate(self):
        for rec in self:
            if rec.attendance_status != 'attended':
                raise UserError(_("Cannot issue certificate: Employee did not attend the course."))
            if rec.score < rec.course_id.passing_score:
                raise UserError(_("Cannot issue certificate: Score %s%% is below passing threshold %s%%.") % (rec.score, rec.course_id.passing_score))
            
            if not rec.certificate_number:
                rec.certificate_number = self.env['ir.sequence'].next_by_code('training.certificate') or _('CERT-%s') % rec.id
            rec.issue_date = fields.Date.today()
            rec.evaluation_result = 'passed'
            rec.certificate_status = 'valid'

    def action_revoke_certificate(self):
        for rec in self:
            rec.certificate_status = 'revoked'

    @api.model
    def _cron_update_certification_status(self):
        """Daily cron checking for certificates expiring within 30 days or expired."""
        today = fields.Date.today()
        warning_window = today + timedelta(days=30)
        
        # Mark expired
        expired_certs = self.search([
            ('certificate_status', 'in', ['valid', 'expiring_soon']),
            ('expiry_date', '<', today)
        ])
        expired_certs.write({'certificate_status': 'expired'})

        # Mark expiring soon
        expiring_certs = self.search([
            ('certificate_status', '=', 'valid'),
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', warning_window)
        ])
        expiring_certs.write({'certificate_status': 'expiring_soon'})

    def action_print_certificate(self):
        self.ensure_one()
        if self.certificate_status not in ['valid', 'expiring_soon']:
            raise UserError(_("Only valid certifications can generate an official Certificate of Completion PDF."))
        return self.env.ref('hr_training_certification_management.action_report_training_certificate').report_action(self)
