# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class TrainingCourse(models.Model):
    _name = 'training.course'
    _description = 'Training Course & Certification Master'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code, name'

    name = fields.Char(string='Course Title', required=True, tracking=True)
    code = fields.Char(string='Course Code', required=True, copy=False, tracking=True)
    category = fields.Selection([
        ('safety', 'Health, Safety & OSHA'),
        ('compliance', 'Regulatory & GMP Compliance'),
        ('technical', 'Technical & Equipment Operation'),
        ('quality', 'ISO & Quality Management'),
        ('cybersecurity', 'IT & Cybersecurity'),
        ('leadership', 'Leadership & Management'),
    ], string='Category', default='safety', required=True, tracking=True)
    
    description = fields.Text(string='Course Objectives & Syllabus')
    duration_hours = fields.Float(string='Duration (Hours)', default=8.0, tracking=True)
    validity_months = fields.Integer(
        string='Validity Period (Months)', 
        default=12, 
        help='Duration before recertification is required. 0 means lifetime validity.'
    )
    passing_score = fields.Float(string='Passing Score (%)', default=80.0, tracking=True)
    
    delivery_mode = fields.Selection([
        ('in_person', 'In-Person Classroom'),
        ('online_live', 'Online Live Webinar'),
        ('self_paced', 'Self-Paced E-Learning'),
        ('hybrid', 'Hybrid / Blended'),
    ], string='Delivery Mode', default='in_person')
    
    training_provider = fields.Char(string='Provider / Certifying Body', default='Internal EHS Department')
    instructor_name = fields.Char(string='Lead Instructor / Assessor')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    # Mandatory Compliance Matrix
    job_ids = fields.Many2many(
        'hr.job', 
        'training_course_job_rel', 
        'course_id', 
        'job_id', 
        string='Mandatory for Job Positions',
        help='Employees holding these positions must hold a valid certificate for this course.'
    )
    department_ids = fields.Many2many(
        'hr.department', 
        'training_course_dept_rel', 
        'course_id', 
        'dept_id', 
        string='Mandatory for Departments'
    )

    # Computed statistics
    session_ids = fields.One2many('training.session', 'course_id', string='Training Sessions')
    participation_ids = fields.One2many('training.participation', 'course_id', string='Training Records')
    
    session_count = fields.Integer(string='Total Sessions', compute='_compute_metrics', store=True)
    certified_count = fields.Integer(string='Certified Personnel', compute='_compute_metrics', store=True)
    compliance_rate = fields.Float(string='Job Compliance %', compute='_compute_compliance_rate')

    @api.constrains('code', 'company_id')
    def _check_code_unique(self):
        for rec in self:
            if rec.code:
                existing = self.search([
                    ('code', '=', rec.code),
                    ('company_id', '=', rec.company_id.id),
                    ('id', '!=', rec.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_('Course code must be unique per company!'))

    @api.constrains('passing_score')
    def _check_passing_score(self):
        for rec in self:
            if rec.passing_score < 0.0 or rec.passing_score > 100.0:
                raise ValidationError(_('Passing score must be between 0 and 100%!'))

    @api.depends('session_ids', 'participation_ids', 'participation_ids.certificate_status')
    def _compute_metrics(self):
        for course in self:
            course.session_count = len(course.session_ids)
            course.certified_count = len(course.participation_ids.filtered(lambda p: p.certificate_status == 'valid'))

    def _compute_compliance_rate(self):
        for course in self:
            # Target employees are active employees in linked jobs or departments
            domain = [('company_id', '=', course.company_id.id)]
            sub_domains = []
            if course.job_ids:
                sub_domains.append(('job_id', 'in', course.job_ids.ids))
            if course.department_ids:
                sub_domains.append(('department_id', 'in', course.department_ids.ids))
            
            if sub_domains:
                if len(sub_domains) == 2:
                    domain.extend(['|'] + sub_domains)
                else:
                    domain.extend(sub_domains)
                
                target_employees = self.env['hr.employee'].search(domain)
                target_count = len(target_employees)
                if target_count > 0:
                    valid_certified_emp_ids = course.participation_ids.filtered(
                        lambda p: p.certificate_status == 'valid' and p.employee_id.id in target_employees.ids
                    ).mapped('employee_id.id')
                    compliant_count = len(set(valid_certified_emp_ids))
                    course.compliance_rate = round((compliant_count / target_count) * 100.0, 1)
                else:
                    course.compliance_rate = 100.0
            else:
                course.compliance_rate = 100.0

    def action_view_sessions(self):
        self.ensure_one()
        return {
            'name': _('Training Sessions - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'training.session',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id)],
            'context': {'default_course_id': self.id},
        }

    def action_view_certified(self):
        self.ensure_one()
        return {
            'name': _('Certified Personnel - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'training.participation',
            'view_mode': 'list,form',
            'domain': [('course_id', '=', self.id), ('certificate_status', '=', 'valid')],
            'context': {'default_course_id': self.id},
        }
