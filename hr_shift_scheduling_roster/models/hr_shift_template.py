# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrShiftTemplate(models.Model):
    _name = 'hr.shift.template'
    _description = 'Shift Definition Template'
    _order = 'start_time asc, id asc'

    name = fields.Char(string='Shift Name', required=True)
    code = fields.Char(string='Shift Code', required=True)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index', default=4)

    shift_type = fields.Selection([
        ('day', 'Day / Morning Shift'),
        ('evening', 'Evening / Afternoon Shift'),
        ('night', 'Night Shift'),
        ('split', 'Split Shift'),
        ('weekend', 'Weekend Duty Shift'),
    ], string='Shift Category', default='day', required=True)

    start_time = fields.Float(string='Start Time (Hour)', default=8.0, required=True, help="e.g. 8.5 for 08:30")
    end_time = fields.Float(string='End Time (Hour)', default=16.5, required=True, help="e.g. 16.5 for 16:30")
    break_duration = fields.Float(string='Unpaid Break (Hours)', default=0.5, help="e.g. 0.5 for 30 minutes")
    duration_hours = fields.Float(string='Net Working Hours', compute='_compute_duration_hours', store=True)

    differential_rate = fields.Float(string='Differential Premium (%)', default=0.0, help="e.g. 15% bonus for night/weekend shifts")
    required_headcount = fields.Integer(string='Standard Required Staff', default=2)
    department_ids = fields.Many2many('hr.department', string='Applicable Departments')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.depends('start_time', 'end_time', 'break_duration')
    def _compute_duration_hours(self):
        for record in self:
            if record.end_time >= record.start_time:
                gross = record.end_time - record.start_time
            else:
                # Overnight shift crossing midnight (e.g. 22:00 to 06:00)
                gross = (24.0 - record.start_time) + record.end_time
            net = max(0.0, gross - (record.break_duration or 0.0))
            record.duration_hours = round(net, 2)

    def name_get(self):
        result = []
        for rec in self:
            sh = int(rec.start_time)
            sm = int(round((rec.start_time - sh) * 60))
            eh = int(rec.end_time)
            em = int(round((rec.end_time - eh) * 60))
            time_str = f"{sh:02d}:{sm:02d} - {eh:02d}:{em:02d}"
            name = f"[{rec.code}] {rec.name} ({time_str})"
            result.append((rec.id, name))
        return result
