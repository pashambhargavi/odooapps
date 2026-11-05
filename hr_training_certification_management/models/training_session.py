# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class TrainingSession(models.Model):
    _name = 'training.session'
    _description = 'Training Batch Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc, id desc'

    name = fields.Char(string='Session Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    course_id = fields.Many2one('training.course', string='Course', required=True, tracking=True)
    course_code = fields.Char(related='course_id.code', string='Course Code', readonly=True)
    category = fields.Selection(related='course_id.category', string='Category', readonly=True)
    
    start_date = fields.Datetime(string='Start Date & Time', required=True, tracking=True)
    end_date = fields.Datetime(string='End Date & Time', required=True, tracking=True)
    location = fields.Char(string='Location / Room / URL', default='Main Training Room A', tracking=True)
    instructor_name = fields.Char(string='Instructor / Trainer', default='Certified Lead Assessor')
    
    max_capacity = fields.Integer(string='Max Capacity', default=25, help='Maximum allowed attendees.')
    notes = fields.Text(string='Session Instructions / Materials')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    
    state = fields.Selection([
        ('draft', 'Draft Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Session'),
        ('completed', 'Completed & Certified'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    participation_ids = fields.One2many('training.participation', 'session_id', string='Attendees & Certifications')
    
    enrolled_count = fields.Integer(string='Enrolled', compute='_compute_counts', store=True)
    attended_count = fields.Integer(string='Attended', compute='_compute_counts', store=True)
    passed_count = fields.Integer(string='Passed & Certified', compute='_compute_counts', store=True)
    pass_rate = fields.Float(string='Pass Rate %', compute='_compute_counts', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('training.session') or _('New')
        return super().create(vals_list)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date <= rec.start_date:
                raise ValidationError(_("End Date must be strictly after Start Date!"))

    @api.depends('participation_ids', 'participation_ids.attendance_status', 'participation_ids.evaluation_result')
    def _compute_counts(self):
        for session in self:
            total = len(session.participation_ids)
            attended = len(session.participation_ids.filtered(lambda p: p.attendance_status == 'attended'))
            passed = len(session.participation_ids.filtered(lambda p: p.evaluation_result == 'passed'))
            session.enrolled_count = total
            session.attended_count = attended
            session.passed_count = passed
            session.pass_rate = round((passed / total * 100.0), 1) if total > 0 else 0.0

    def action_confirm(self):
        for session in self:
            session.state = 'confirmed'

    def action_start(self):
        for session in self:
            session.state = 'in_progress'

    def action_complete(self):
        for session in self:
            if not session.participation_ids:
                raise UserError(_("Cannot complete session without attendees."))
            # Process certificates for passing attendees
            for part in session.participation_ids:
                if part.attendance_status == 'attended' and part.score >= session.course_id.passing_score:
                    part.evaluation_result = 'passed'
                    part.action_issue_certificate()
                elif part.attendance_status == 'attended':
                    part.evaluation_result = 'failed'
            session.state = 'completed'

    def action_cancel(self):
        for session in self:
            session.state = 'cancelled'

    def action_auto_enroll_mandatory(self):
        """Auto enroll employees who are in the mandatory job position or department and currently lack valid certification."""
        self.ensure_one()
        course = self.course_id
        if not course.job_ids and not course.department_ids:
            raise UserError(_("This course has no mandatory job positions or departments configured in its Compliance Matrix."))

        domain = [('company_id', '=', self.company_id.id)]
        sub_domains = []
        if course.job_ids:
            sub_domains.append(('job_id', 'in', course.job_ids.ids))
        if course.department_ids:
            sub_domains.append(('department_id', 'in', course.department_ids.ids))
        
        if len(sub_domains) == 2:
            domain.extend(['|'] + sub_domains)
        else:
            domain.extend(sub_domains)
        
        target_employees = self.env['hr.employee'].search(domain)
        existing_attendees = self.participation_ids.mapped('employee_id')
        
        # Check who has a currently valid certificate
        valid_certs = self.env['training.participation'].search([
            ('course_id', '=', course.id),
            ('certificate_status', '=', 'valid')
        ])
        certified_employee_ids = valid_certs.mapped('employee_id.id')

        enrolled_count = 0
        current_slots = self.max_capacity - len(self.participation_ids)
        for emp in target_employees:
            if emp.id not in certified_employee_ids and emp not in existing_attendees:
                if current_slots <= 0:
                    break
                self.env['training.participation'].create({
                    'session_id': self.id,
                    'course_id': course.id,
                    'employee_id': emp.id,
                    'attendance_status': 'registered',
                })
                current_slots -= 1
                enrolled_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Auto-Enrollment Complete'),
                'message': _('Successfully enrolled %s non-compliant employee(s) into this session.') % enrolled_count,
                'type': 'success',
                'sticky': False,
            }
        }
