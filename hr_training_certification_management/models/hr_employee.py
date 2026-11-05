# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    training_participation_ids = fields.One2many('training.participation', 'employee_id', string='Training Records')
    
    valid_certification_count = fields.Integer(string='Valid Certifications', compute='_compute_training_stats')
    expiring_certification_count = fields.Integer(string='Expiring Certifications', compute='_compute_training_stats')
    has_certification_warning = fields.Boolean(string='Has Training Warning', compute='_compute_training_stats')

    def _compute_training_stats(self):
        for emp in self:
            records = emp.training_participation_ids
            valid = len(records.filtered(lambda r: r.certificate_status == 'valid'))
            expiring = len(records.filtered(lambda r: r.certificate_status == 'expiring_soon'))
            expired = len(records.filtered(lambda r: r.certificate_status == 'expired'))
            emp.valid_certification_count = valid
            emp.expiring_certification_count = expiring
            emp.has_certification_warning = bool(expiring > 0 or expired > 0)

    def action_view_employee_certifications(self):
        self.ensure_one()
        return {
            'name': _('Certificates & Training Records - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'training.participation',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
