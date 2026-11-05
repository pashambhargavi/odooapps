# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class TrainingComplianceMatrix(models.Model):
    _name = 'training.compliance.matrix'
    _description = 'Department & Job Compliance Audit Matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Audit Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    department_id = fields.Many2one('hr.department', string='Target Department', tracking=True)
    job_id = fields.Many2one('hr.job', string='Target Job Position', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    total_requirements = fields.Integer(string='Mandatory Requirements Count', compute='_compute_audit_summary', store=True)
    compliant_count = fields.Integer(string='Compliant Certified', compute='_compute_audit_summary', store=True)
    gap_count = fields.Integer(string='Non-Compliant Gaps', compute='_compute_audit_summary', store=True)
    compliance_score = fields.Float(string='Compliance Score %', compute='_compute_audit_summary', store=True)
    
    line_ids = fields.One2many('training.compliance.matrix.line', 'matrix_id', string='Employee Compliance Lines')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('training.compliance.matrix') or _('AUD/%s') % fields.Date.today().year
        return super().create(vals_list)

    @api.depends('line_ids', 'line_ids.status')
    def _compute_audit_summary(self):
        for rec in self:
            total = len(rec.line_ids)
            compliant = len(rec.line_ids.filtered(lambda l: l.status in ['compliant', 'expiring_soon']))
            gaps = len(rec.line_ids.filtered(lambda l: l.status in ['missing', 'expired']))
            rec.total_requirements = total
            rec.compliant_count = compliant
            rec.gap_count = gaps
            rec.compliance_score = round((compliant / total * 100.0), 1) if total > 0 else 100.0

    def action_generate_audit_lines(self):
        """Scans all active employees matching target department/job and evaluates mandatory course status."""
        self.ensure_one()
        self.line_ids.unlink()

        domain = [('company_id', '=', self.company_id.id)]
        if self.department_id:
            domain.append(('department_id', '=', self.department_id.id))
        if self.job_id:
            domain.append(('job_id', '=', self.job_id.id))
        
        employees = self.env['hr.employee'].search(domain)
        all_courses = self.env['training.course'].search([('company_id', '=', self.company_id.id)])

        lines_to_create = []
        for emp in employees:
            # Find courses mandatory for this employee's job or department
            mandatory_courses = all_courses.filtered(
                lambda c: (emp.job_id and emp.job_id in c.job_ids) or 
                          (emp.department_id and emp.department_id in c.department_ids)
            )

            for course in mandatory_courses:
                # Find latest valid or expired participation record
                part = self.env['training.participation'].search([
                    ('employee_id', '=', emp.id),
                    ('course_id', '=', course.id),
                    ('certificate_status', 'in', ['valid', 'expiring_soon', 'expired'])
                ], order='issue_date desc', limit=1)

                if not part:
                    status = 'missing'
                    last_issue = False
                    expiry = False
                elif part.certificate_status == 'expired':
                    status = 'expired'
                    last_issue = part.issue_date
                    expiry = part.expiry_date
                elif part.certificate_status == 'expiring_soon':
                    status = 'expiring_soon'
                    last_issue = part.issue_date
                    expiry = part.expiry_date
                else:
                    status = 'compliant'
                    last_issue = part.issue_date
                    expiry = part.expiry_date

                lines_to_create.append({
                    'matrix_id': self.id,
                    'employee_id': emp.id,
                    'job_id': emp.job_id.id if emp.job_id else False,
                    'department_id': emp.department_id.id if emp.department_id else False,
                    'course_id': course.id,
                    'status': status,
                    'last_certified_date': last_issue,
                    'expiry_date': expiry,
                })

        if lines_to_create:
            self.env['training.compliance.matrix.line'].create(lines_to_create)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Audit Matrix Generated'),
                'message': _('Audited %s mandatory training requirements across %s employee(s).') % (len(lines_to_create), len(employees)),
                'type': 'success',
                'sticky': False,
            }
        }


class TrainingComplianceMatrixLine(models.Model):
    _name = 'training.compliance.matrix.line'
    _description = 'Employee Compliance Audit Line'
    _order = 'status, employee_id'

    matrix_id = fields.Many2one('training.compliance.matrix', string='Audit Matrix', ondelete='cascade', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    job_id = fields.Many2one('hr.job', string='Job Position')
    department_id = fields.Many2one('hr.department', string='Department')
    course_id = fields.Many2one('training.course', string='Mandatory Course', required=True)
    category = fields.Selection(related='course_id.category', string='Category', readonly=True)
    
    status = fields.Selection([
        ('compliant', 'Fully Compliant'),
        ('expiring_soon', 'Expiring Soon (<30d)'),
        ('expired', 'Expired (Violation)'),
        ('missing', 'Missing (Never Certified)'),
    ], string='Compliance Status', required=True, default='missing')

    last_certified_date = fields.Date(string='Last Certified')
    expiry_date = fields.Date(string='Certificate Expiry')
