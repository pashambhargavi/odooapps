# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HelpdeskTeam(models.Model):
    _name = 'helpdesk.team'
    _description = 'Helpdesk Support Team'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(string='Team Name', required=True, translate=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index', default=0)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    leader_id = fields.Many2one(
        'res.users', string='Team Leader',
        default=lambda self: self.env.user, tracking=True,
        domain="[('share', '=', False)]",
    )
    member_ids = fields.Many2many(
        'res.users',
        'helpdesk_team_res_users_rel',
        'team_id', 'user_id',
        string='Support Agents',
        domain="[('share', '=', False)]",
    )
    assignment_method = fields.Selection([
        ('manual', 'Manual Assignment'),
        ('balanced', 'Auto-Assign (Least Loaded Agent)'),
    ], string='Assignment Mode', default='balanced', required=True, tracking=True)
    use_sla = fields.Boolean(string='Enforce SLA Policies', default=True, tracking=True)
    description = fields.Text(string='Team Description', translate=True)

    ticket_ids = fields.One2many('helpdesk.ticket', 'team_id', string='Tickets')
    open_ticket_count = fields.Integer(
        string='Open Tickets', compute='_compute_ticket_stats',
    )
    unassigned_ticket_count = fields.Integer(
        string='Unassigned Tickets', compute='_compute_ticket_stats',
    )
    urgent_ticket_count = fields.Integer(
        string='High / Urgent Tickets', compute='_compute_ticket_stats',
    )
    sla_failed_count = fields.Integer(
        string='SLA Breached', compute='_compute_ticket_stats',
    )

    @api.depends(
        'ticket_ids.stage_id.is_close',
        'ticket_ids.stage_id.is_cancel',
        'ticket_ids.user_id',
        'ticket_ids.priority',
        'ticket_ids.sla_status',
    )
    def _compute_ticket_stats(self):
        for team in self:
            open_tickets = team.ticket_ids.filtered(
                lambda t: not t.stage_id.is_close and not t.stage_id.is_cancel
            )
            team.open_ticket_count = len(open_tickets)
            team.unassigned_ticket_count = len(open_tickets.filtered(lambda t: not t.user_id))
            team.urgent_ticket_count = len(open_tickets.filtered(lambda t: t.priority in ('2', '3')))
            team.sla_failed_count = len(open_tickets.filtered(lambda t: t.sla_status == 'failed'))

    def _get_next_assigned_user(self):
        self.ensure_one()
        if self.assignment_method != 'balanced' or not self.member_ids:
            return self.leader_id
        # Pick the support agent with the fewest open tickets in this team
        open_tickets = self.ticket_ids.filtered(
            lambda t: not t.stage_id.is_close and not t.stage_id.is_cancel
        )
        agent_counts = {member: 0 for member in self.member_ids}
        for ticket in open_tickets:
            if ticket.user_id in agent_counts:
                agent_counts[ticket.user_id] += 1
        return min(agent_counts, key=agent_counts.get)

    def action_view_team_tickets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s Tickets') % self.name,
            'res_model': 'helpdesk.ticket',
            'view_mode': 'kanban,list,form,pivot,graph,activity',
            'domain': [('team_id', '=', self.id)],
            'context': {
                'default_team_id': self.id,
                'search_default_open_tickets': 1,
            },
        }

    def action_create_ticket(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Support Ticket'),
            'res_model': 'helpdesk.ticket',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_team_id': self.id,
            },
        }
