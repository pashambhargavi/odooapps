# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    shift_schedule_ids = fields.One2many('hr.shift.schedule', 'employee_id', string='Assigned Shifts')
    shift_count = fields.Integer(string='Scheduled Shifts Count', compute='_compute_shift_count')
    weekly_max_hours = fields.Float(string='Weekly Work Limit (Hours)', default=40.0)

    @api.depends('shift_schedule_ids')
    def _compute_shift_count(self):
        for employee in self:
            employee.shift_count = len(employee.shift_schedule_ids)

    def action_view_shifts(self):
        self.ensure_one()
        action = self.env.ref('hr_shift_scheduling_roster.action_hr_shift_schedule').read()[0]
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action
