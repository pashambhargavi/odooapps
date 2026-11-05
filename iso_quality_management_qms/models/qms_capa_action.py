# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class QmsCapaAction(models.Model):
    _name = 'qms.capa.action'
    _description = 'CAPA Corrective & Preventive Action Plan Line'
    _order = 'deadline asc, id asc'

    capa_id = fields.Many2one('qms.capa', string='CAPA Investigation', required=True, ondelete='cascade')
    name = fields.Char(string='Action Description & Deliverable', required=True)
    action_type = fields.Selection([
        ('containment', 'Immediate Containment'),
        ('corrective', 'Permanent Corrective Action'),
        ('preventive', 'Preventive / Mistake-Proofing (Poka-Yoke)'),
        ('training', 'Personnel Retraining & Competence Evaluation'),
        ('sop_update', 'SOP / Work Instruction Revision'),
    ], string='Action Category', default='corrective', required=True)

    assigned_to_id = fields.Many2one('res.users', string='Action Owner', default=lambda self: self.env.user, required=True)
    deadline = fields.Date(string='Target Deadline', required=True, default=fields.Date.today)
    completion_date = fields.Date(string='Completion Date')
    state = fields.Selection([
        ('draft', 'Planned'),
        ('in_progress', 'In Execution'),
        ('completed', 'Completed'),
        ('verified', 'Verified Effective'),
    ], string='Status', default='draft', required=True)

    evidence_notes = fields.Text(string='Implementation Evidence / Verification Notes')

    def action_start(self):
        for record in self:
            record.write({'state': 'in_progress'})

    def action_complete(self):
        for record in self:
            record.write({
                'state': 'completed',
                'completion_date': fields.Date.today(),
            })

    def action_verify(self):
        for record in self:
            record.write({'state': 'verified'})
