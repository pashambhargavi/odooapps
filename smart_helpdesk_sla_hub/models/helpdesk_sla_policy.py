# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskSlaPolicy(models.Model):
    _name = 'helpdesk.sla.policy'
    _description = 'Helpdesk SLA Policy'
    _order = 'sequence, priority desc, id'
    _check_company_auto = True

    name = fields.Char(string='SLA Policy Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    team_id = fields.Many2one(
        'helpdesk.team', string='Support Team',
        required=True, ondelete='cascade', check_company=True,
    )
    ticket_type_id = fields.Many2one(
        'helpdesk.ticket.type', string='Ticket Type',
        help='Leave empty to apply to all ticket types.',
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Minimum Priority', default='0', required=True)

    response_time_hours = fields.Float(
        string='Target First Response (Hours)',
        default=4.0, required=True,
        help='Maximum hours allowed to send first response or move ticket to In Progress.',
    )
    resolution_time_hours = fields.Float(
        string='Target Resolution (Hours)',
        default=24.0, required=True,
        help='Maximum hours allowed to resolve the ticket.',
    )
    description = fields.Text(string='SLA Policy Terms')

    @api.constrains('response_time_hours', 'resolution_time_hours')
    def _check_positive_hours(self):
        for policy in self:
            if policy.response_time_hours <= 0 or policy.resolution_time_hours <= 0:
                raise ValidationError(_('SLA response and resolution hours must be greater than 0.'))
            if policy.response_time_hours > policy.resolution_time_hours:
                raise ValidationError(_('Target First Response hours cannot exceed Target Resolution hours.'))

    @api.model
    def _find_matching_sla(self, team, priority='0', ticket_type=False):
        if not team or not team.use_sla:
            return self.browse()
        policies = self.search([
            ('team_id', '=', team.id),
            ('active', '=', True),
        ], order='sequence, priority desc, id')
        for policy in policies:
            if policy.ticket_type_id and ticket_type and policy.ticket_type_id != ticket_type:
                continue
            if policy.ticket_type_id and not ticket_type:
                continue
            if int(priority or '0') >= int(policy.priority or '0'):
                return policy
        return self.browse()
