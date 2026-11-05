# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrShiftSchedule(models.Model):
    _name = 'hr.shift.schedule'
    _description = 'Individual Shift Assignment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date asc, shift_template_id asc, id asc'

    name = fields.Char(string='Shift Summary', compute='_compute_name')
    roster_id = fields.Many2one('hr.shift.roster', string='Master Roster', ondelete='cascade', tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Assigned Employee', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='roster_id.department_id', store=True)

    shift_template_id = fields.Many2one('hr.shift.template', string='Shift Template', required=True, tracking=True)
    date = fields.Date(string='Shift Date', required=True, default=fields.Date.today, tracking=True)

    start_datetime = fields.Datetime(string='Start Timestamp', compute='_compute_datetimes', store=True)
    end_datetime = fields.Datetime(string='End Timestamp', compute='_compute_datetimes', store=True)

    planned_hours = fields.Float(string='Planned Hours', related='shift_template_id.duration_hours', store=True)
    differential_rate = fields.Float(string='Premium %', related='shift_template_id.differential_rate', store=True)
    color = fields.Integer(string='Color', related='shift_template_id.color')

    is_open_shift = fields.Boolean(string='Open for Bidding', default=True, compute='_compute_is_open', store=True, readonly=False)
    has_conflict = fields.Boolean(string='Has Conflict', default=False, tracking=True)
    conflict_reason = fields.Char(string='Conflict Note')

    state = fields.Selection([
        ('draft', 'Draft Slot'),
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Staff Confirmed'),
        ('swapped', 'Shift Swapped'),
        ('absent', 'No-Show / Absent'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    swap_request_ids = fields.One2many('hr.shift.swap.request', 'original_shift_id', string='Swap Requests')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('shift_template_id', 'employee_id', 'date')
    def _compute_name(self):
        for record in self:
            code = record.shift_template_id.code if record.shift_template_id else 'SHIFT'
            emp_name = record.employee_id.name if record.employee_id else _('UNASSIGNED')
            d_str = record.date.strftime('%d/%m/%Y') if record.date else ''
            record.name = f"[{code}] {emp_name} - {d_str}"

    @api.depends('employee_id')
    def _compute_is_open(self):
        for record in self:
            if record.employee_id:
                record.is_open_shift = False
            else:
                record.is_open_shift = True

    @api.depends('date', 'shift_template_id', 'shift_template_id.start_time', 'shift_template_id.end_time')
    def _compute_datetimes(self):
        for record in self:
            if record.date and record.shift_template_id:
                tmpl = record.shift_template_id
                sh = int(tmpl.start_time)
                sm = int(round((tmpl.start_time - sh) * 60))
                eh = int(tmpl.end_time)
                em = int(round((tmpl.end_time - eh) * 60))

                start_dt = datetime.combine(record.date, time(sh, sm))
                if tmpl.end_time >= tmpl.start_time:
                    end_dt = datetime.combine(record.date, time(eh, em))
                else:
                    # Next day overnight
                    end_dt = datetime.combine(record.date + timedelta(days=1), time(eh, em))

                record.start_datetime = start_dt
                record.end_datetime = end_dt
            else:
                record.start_datetime = False
                record.end_datetime = False

    def action_confirm_attendance(self):
        for record in self:
            record.write({'state': 'confirmed'})

    def action_claim_open_shift(self):
        self.ensure_one()
        employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
        if not employee:
            raise UserError(_("No employee profile found for your user account."))
        self.write({
            'employee_id': employee.id,
            'is_open_shift': False,
            'state': 'confirmed',
        })

    def action_mark_absent(self):
        for record in self:
            record.write({'state': 'absent'})

    def action_request_swap(self):
        self.ensure_one()
        if not self.employee_id:
            raise UserError(_("Cannot initiate a swap request for an unassigned shift."))
        return {
            'name': _('Request Shift Swap'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.shift.swap.request',
            'view_mode': 'form',
            'context': {
                'default_original_shift_id': self.id,
                'default_requesting_employee_id': self.employee_id.id,
            },
            'target': 'new',
        }
