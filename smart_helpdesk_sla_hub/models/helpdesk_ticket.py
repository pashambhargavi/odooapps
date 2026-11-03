# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, id desc'
    _check_company_auto = True

    def _default_stage_id(self):
        return self.env['helpdesk.stage'].search([], order='sequence, id', limit=1)

    def _default_team_id(self):
        return self.env['helpdesk.team'].search([], order='sequence, id', limit=1)

    name = fields.Char(string='Subject', required=True, tracking=True, index='trigram')
    ticket_ref = fields.Char(
        string='Ticket Number', required=True, copy=False,
        readonly=True, default=lambda self: _('New'), index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    team_id = fields.Many2one(
        'helpdesk.team', string='Support Team',
        default=_default_team_id, required=True,
        tracking=True, index=True, check_company=True,
    )
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Stage',
        default=_default_stage_id, required=True,
        tracking=True, index=True, copy=False,
        group_expand='_read_group_stage_ids',
    )
    is_close = fields.Boolean(related='stage_id.is_close', store=True)
    is_cancel = fields.Boolean(related='stage_id.is_cancel', store=True)

    user_id = fields.Many2one(
        'res.users', string='Assigned To',
        tracking=True, index=True, check_company=True,
        domain="[('share', '=', False)]",
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        tracking=True, index=True, check_company=True,
    )
    partner_email = fields.Char(
        string='Customer Email',
        compute='_compute_partner_contact', store=True, readonly=False,
    )
    partner_phone = fields.Char(
        string='Customer Phone',
        compute='_compute_partner_contact', store=True, readonly=False,
    )
    ticket_type_id = fields.Many2one(
        'helpdesk.ticket.type', string='Ticket Type', tracking=True,
    )
    tag_ids = fields.Many2many(
        'helpdesk.tag', string='Tags',
    )
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1', required=True, tracking=True)
    channel = fields.Selection([
        ('email', 'Email'),
        ('phone', 'Phone Call'),
        ('web', 'Web / Portal'),
        ('social', 'Chat / Social'),
        ('internal', 'Internal Escalation'),
    ], string='Channel', default='email', required=True, tracking=True)

    # Linked business documents
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order',
        check_company=True, tracking=True,
        domain="[('partner_id', '=?', partner_id)]",
    )
    invoice_id = fields.Many2one(
        'account.move', string='Related Invoice / Bill',
        check_company=True, tracking=True,
        domain="[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice')), ('partner_id', '=?', partner_id)]",
    )
    product_id = fields.Many2one(
        'product.product', string='Affected Product',
        check_company=True, tracking=True,
    )

    description = fields.Html(string='Issue Description')
    resolution_summary = fields.Text(string='Resolution Summary', tracking=True)

    # SLA & Timestamps
    sla_policy_id = fields.Many2one(
        'helpdesk.sla.policy', string='Applied SLA Policy',
        readonly=True, copy=False, tracking=True,
    )
    sla_response_deadline = fields.Datetime(
        string='SLA Response Deadline', readonly=True, copy=False, tracking=True,
    )
    sla_deadline = fields.Datetime(
        string='SLA Resolution Deadline', readonly=True, copy=False, tracking=True,
    )
    first_response_date = fields.Datetime(
        string='First Response On', readonly=True, copy=False, tracking=True,
    )
    closed_date = fields.Datetime(
        string='Resolved On', readonly=True, copy=False, tracking=True,
    )
    response_hours = fields.Float(
        string='First Response Time (Hours)',
        compute='_compute_durations', store=True,
    )
    resolution_hours = fields.Float(
        string='Total Resolution Time (Hours)',
        compute='_compute_durations', store=True,
    )
    sla_status = fields.Selection([
        ('none', 'No SLA'),
        ('ongoing', 'On Track'),
        ('achieved', 'SLA Achieved'),
        ('failed', 'SLA Breached'),
    ], string='SLA Status', compute='_compute_sla_status', store=True, tracking=True)

    customer_rating = fields.Selection([
        ('0', 'Not Rated'),
        ('1', '1 - Very Dissatisfied'),
        ('2', '2 - Dissatisfied'),
        ('3', '3 - Neutral'),
        ('4', '4 - Satisfied'),
        ('5', '5 - Very Satisfied'),
    ], string='Customer Rating', default='0', tracking=True)
    customer_feedback = fields.Text(string='Customer Feedback')
    color = fields.Integer(string='Color Index', default=0)

    @api.model
    def _read_group_stage_ids(self, stages, domain):
        return self.env['helpdesk.stage'].search([], order='sequence, id')

    @api.depends('partner_id')
    def _compute_partner_contact(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_email = ticket.partner_id.email
                ticket.partner_phone = ticket.partner_id.phone

    @api.depends('create_date', 'first_response_date', 'closed_date')
    def _compute_durations(self):
        for ticket in self:
            if ticket.create_date and ticket.first_response_date:
                delta_resp = ticket.first_response_date - ticket.create_date
                ticket.response_hours = round(max(delta_resp.total_seconds() / 3600.0, 0.0), 2)
            else:
                ticket.response_hours = 0.0

            if ticket.create_date and ticket.closed_date:
                delta_close = ticket.closed_date - ticket.create_date
                ticket.resolution_hours = round(max(delta_close.total_seconds() / 3600.0, 0.0), 2)
            else:
                ticket.resolution_hours = 0.0

    @api.depends('sla_policy_id', 'sla_deadline', 'closed_date', 'stage_id.is_close', 'stage_id.is_cancel')
    def _compute_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.sla_policy_id or not ticket.sla_deadline or ticket.stage_id.is_cancel:
                ticket.sla_status = 'none'
            elif ticket.stage_id.is_close:
                compare_time = ticket.closed_date or now
                ticket.sla_status = 'achieved' if compare_time <= ticket.sla_deadline else 'failed'
            else:
                ticket.sla_status = 'failed' if now > ticket.sla_deadline else 'ongoing'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ticket_ref', _('New')) == _('New'):
                vals['ticket_ref'] = self.env['ir.sequence'].next_by_code('helpdesk.ticket') or _('New')
            if not vals.get('user_id') and vals.get('team_id'):
                team = self.env['helpdesk.team'].browse(vals['team_id'])
                assigned = team._get_next_assigned_user()
                if assigned:
                    vals['user_id'] = assigned.id
        tickets = super().create(vals_list)
        for ticket in tickets:
            ticket._apply_sla_policy()
        return tickets

    def write(self, vals):
        now = fields.Datetime.now()
        if 'stage_id' in vals:
            new_stage = self.env['helpdesk.stage'].browse(vals['stage_id'])
            for ticket in self:
                if new_stage.is_in_progress and not ticket.first_response_date:
                    vals.setdefault('first_response_date', now)
                if new_stage.is_close and not ticket.closed_date:
                    vals.setdefault('closed_date', now)
                    if not ticket.first_response_date:
                        vals.setdefault('first_response_date', now)
        res = super().write(vals)
        if any(f in vals for f in ('team_id', 'priority', 'ticket_type_id')):
            for ticket in self.filtered(lambda t: not t.stage_id.is_close and not t.stage_id.is_cancel):
                ticket._apply_sla_policy()
        return res

    def _apply_sla_policy(self):
        for ticket in self:
            policy = self.env['helpdesk.sla.policy']._find_matching_sla(
                ticket.team_id,
                ticket.priority,
                ticket.ticket_type_id,
            )
            if policy:
                base_time = ticket.create_date or fields.Datetime.now()
                ticket.write({
                    'sla_policy_id': policy.id,
                    'sla_response_deadline': base_time + timedelta(hours=policy.response_time_hours),
                    'sla_deadline': base_time + timedelta(hours=policy.resolution_time_hours),
                })
            else:
                ticket.write({
                    'sla_policy_id': False,
                    'sla_response_deadline': False,
                    'sla_deadline': False,
                })

    def action_assign_to_me(self):
        for ticket in self:
            ticket.user_id = self.env.user
        return True

    def action_start_progress(self):
        in_progress_stage = self.env['helpdesk.stage'].search([('is_in_progress', '=', True)], order='sequence, id', limit=1)
        for ticket in self:
            vals = {}
            if not ticket.user_id:
                vals['user_id'] = self.env.user.id
            if not ticket.first_response_date:
                vals['first_response_date'] = fields.Datetime.now()
            if in_progress_stage:
                vals['stage_id'] = in_progress_stage.id
            ticket.write(vals)
        return True

    def action_open_resolve_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Resolve Support Ticket'),
            'res_model': 'helpdesk.ticket.resolve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_resolution_summary': self.resolution_summary or '',
            },
        }

    def action_reopen_ticket(self):
        in_progress_stage = self.env['helpdesk.stage'].search([('is_in_progress', '=', True)], order='sequence, id', limit=1)
        fallback_stage = in_progress_stage or self._default_stage_id()
        for ticket in self:
            ticket.write({
                'stage_id': fallback_stage.id,
                'closed_date': False,
            })
            ticket.message_post(body=_('Ticket reopened by <b>%s</b>.') % self.env.user.name)
        return True

    @api.model
    def _cron_check_sla_breaches(self):
        now = fields.Datetime.now()
        breached_tickets = self.search([
            ('sla_policy_id', '!=', False),
            ('sla_deadline', '<', now),
            ('is_close', '=', False),
            ('is_cancel', '=', False),
            ('sla_status', '!=', 'failed'),
        ])
        for ticket in breached_tickets:
            ticket.sla_status = 'failed'
            target_user = ticket.user_id or ticket.team_id.leader_id or self.env.user
            ticket.activity_schedule(
                'mail.mail_activity_data_warning',
                user_id=target_user.id,
                summary=_('SLA Breached: %s') % ticket.ticket_ref,
                note=_('Ticket %s (%s) has exceeded its SLA Resolution Deadline (%s).') % (
                    ticket.ticket_ref, ticket.name, ticket.sla_deadline
                ),
            )
            ticket.message_post(
                body=_('<b>SLA Breach Alert:</b> Resolution deadline (%s) has passed.') % ticket.sla_deadline,
            )
