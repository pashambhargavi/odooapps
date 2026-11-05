# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    gratuity_settlement_ids = fields.One2many(
        'hr.gratuity.settlement',
        'employee_id',
        string='End of Service Settlements'
    )
    gratuity_settlement_count = fields.Integer(
        string='EOS Settlements Count',
        compute='_compute_gratuity_settlement_count'
    )

    @api.depends('gratuity_settlement_ids')
    def _compute_gratuity_settlement_count(self):
        for emp in self:
            emp.gratuity_settlement_count = len(emp.gratuity_settlement_ids)

    def action_view_gratuity_settlements(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("hr_gratuity_settlement_calculator.action_hr_gratuity_settlement")
        action['domain'] = [('employee_id', '=', self.id)]
        action['context'] = {'default_employee_id': self.id}
        return action
