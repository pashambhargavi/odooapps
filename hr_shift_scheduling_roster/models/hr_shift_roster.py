# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrShiftRoster(models.Model):
    _name = 'hr.shift.roster'
    _description = 'Master Duty Roster Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc, id desc'

    name = fields.Char(
        string='Roster Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    title = fields.Char(string='Roster Title', required=True, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department / Branch', required=True, tracking=True)
    manager_id = fields.Many2one('res.users', string='Roster Planner', default=lambda self: self.env.user, required=True, tracking=True)

    date_start = fields.Date(string='Schedule Start Date', required=True, tracking=True, default=fields.Date.today)
    date_end = fields.Date(string='Schedule End Date', required=True, tracking=True,
                           default=lambda self: fields.Date.today() + timedelta(days=6))

    state = fields.Selection([
        ('draft', 'Draft Planning'),
        ('confirmed', 'Ready for Review'),
        ('published', 'Published & Active'),
        ('closed', 'Completed & Archived'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    shift_line_ids = fields.One2many('hr.shift.schedule', 'roster_id', string='Scheduled Shifts')

    total_shifts_count = fields.Integer(string='Total Shifts', compute='_compute_roster_metrics', store=True)
    unassigned_shifts_count = fields.Integer(string='Open / Unassigned Shifts', compute='_compute_roster_metrics', store=True)
    total_planned_hours = fields.Float(string='Total Scheduled Hours', compute='_compute_roster_metrics', store=True)
    conflict_count = fields.Integer(string='Schedule Conflicts', compute='_compute_roster_metrics', store=True)

    note = fields.Text(string='Internal Planning Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.shift.roster') or _('New')
        return super().create(vals_list)

    @api.depends('shift_line_ids', 'shift_line_ids.employee_id', 'shift_line_ids.planned_hours', 'shift_line_ids.has_conflict')
    def _compute_roster_metrics(self):
        for record in self:
            shifts = record.shift_line_ids
            record.total_shifts_count = len(shifts)
            record.unassigned_shifts_count = len(shifts.filtered(lambda s: not s.employee_id))
            record.total_planned_hours = sum(shifts.mapped('planned_hours'))
            record.conflict_count = len(shifts.filtered(lambda s: s.has_conflict))

    def action_generate_slots(self):
        self.ensure_one()
        if self.date_end < self.date_start:
            raise UserError(_("The Roster End Date cannot be earlier than the Start Date."))

        templates = self.env['hr.shift.template'].search([
            ('active', '=', True),
            '|', ('department_ids', '=', False), ('department_ids', 'in', self.department_id.id)
        ])
        if not templates:
            templates = self.env['hr.shift.template'].search([('active', '=', True)], limit=3)

        if not templates:
            raise UserError(_("No active Shift Templates found. Please define shift templates first."))

        # Generate slots for each day in range
        current_date = self.date_start
        new_shifts = []
        while current_date <= self.date_end:
            for tmpl in templates:
                headcount = tmpl.required_headcount or 1
                for _ in range(headcount):
                    new_shifts.append((0, 0, {
                        'shift_template_id': tmpl.id,
                        'department_id': self.department_id.id,
                        'date': current_date,
                        'company_id': self.company_id.id,
                    }))
            current_date += timedelta(days=1)

        self.write({'shift_line_ids': new_shifts})

    def action_auto_schedule(self):
        self.ensure_one()
        # Find employees in this department
        employees = self.env['hr.employee'].search([
            ('department_id', '=', self.department_id.id),
            ('active', '=', True)
        ])
        if not employees:
            employees = self.env['hr.employee'].search([('active', '=', True)], limit=10)

        if not employees:
            raise UserError(_("No active employees found to assign to this roster."))

        emp_list = list(employees)
        emp_idx = 0
        unassigned = self.shift_line_ids.filtered(lambda s: not s.employee_id)
        for shift in unassigned:
            emp = emp_list[emp_idx % len(emp_list)]
            shift.write({'employee_id': emp.id, 'is_open_shift': False})
            emp_idx += 1

        self.action_check_conflicts()

    def action_check_conflicts(self):
        for record in self:
            # Check for same employee having multiple overlapping shifts on the same date
            emp_shifts = {}
            for shift in record.shift_line_ids:
                shift.has_conflict = False
                shift.conflict_reason = False
                if shift.employee_id:
                    key = (shift.employee_id.id, shift.date)
                    if key in emp_shifts:
                        # Overlap detected
                        shift.has_conflict = True
                        shift.conflict_reason = _("Double-booked: Employee is already scheduled on this day.")
                        prev_shift = emp_shifts[key]
                        prev_shift.has_conflict = True
                        prev_shift.conflict_reason = _("Double-booked: Employee is scheduled on another shift on this day.")
                    else:
                        emp_shifts[key] = shift

    def action_confirm(self):
        for record in self:
            record.write({'state': 'confirmed'})

    def action_publish(self):
        for record in self:
            record.action_check_conflicts()
            record.write({'state': 'published'})
            # Mark scheduled shifts as confirmed
            for s in record.shift_line_ids:
                if s.employee_id and s.state == 'draft':
                    s.write({'state': 'scheduled'})

    def action_close(self):
        for record in self:
            record.write({'state': 'closed'})
            for s in record.shift_line_ids:
                if s.state in ('draft', 'scheduled', 'confirmed'):
                    s.write({'state': 'completed'})

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancelled'})
