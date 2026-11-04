# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    followup_status = fields.Selection([
        ('no_action', 'No Action Needed'),
        ('with_overdue', 'Overdue Balance Pending'),
        ('in_need_of_action', 'Action Due Today'),
        ('on_hold', 'Credit Hold Applied'),
    ], string='Dunning Status', compute='_compute_followup_metrics', search='_search_followup_status')

    latest_followup_level_id = fields.Many2one(
        'account.followup.level',
        string='Current Dunning Level',
        tracking=True
    )
    latest_followup_date = fields.Date(
        string='Latest Follow-up Date',
        tracking=True
    )
    next_followup_date = fields.Date(
        string='Next Action Date',
        tracking=True
    )
    exclude_from_followup = fields.Boolean(
        string='Exclude from Automated Dunning',
        default=False,
        help='Check to exclude this customer from automated reminder emails and escalations.'
    )
    total_overdue_amount = fields.Monetary(
        string='Total Overdue Amount',
        compute='_compute_followup_metrics',
        currency_field='currency_id'
    )
    total_due_amount = fields.Monetary(
        string='Total Outstanding Due',
        compute='_compute_followup_metrics',
        currency_field='currency_id'
    )
    unpaid_invoice_count = fields.Integer(
        string='Unpaid Invoices',
        compute='_compute_followup_metrics'
    )
    max_days_overdue = fields.Integer(
        string='Max Days Overdue',
        compute='_compute_followup_metrics'
    )
    followup_history_ids = fields.One2many(
        'account.followup.history',
        'partner_id',
        string='Follow-up History'
    )

    def _get_unpaid_customer_invoices(self):
        """Fetch all posted, unpaid or partially paid out_invoices for this partner."""
        self.ensure_one()
        return self.env['account.move'].search([
            ('partner_id', 'child_of', self.commercial_partner_id.id),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ])

    def _compute_followup_metrics(self):
        today = fields.Date.context_today(self)
        for partner in self:
            invoices = partner._get_unpaid_customer_invoices()
            partner.unpaid_invoice_count = len(invoices)
            
            total_due = sum(inv.amount_residual for inv in invoices)
            overdue_invs = [inv for inv in invoices if inv.invoice_date_due and inv.invoice_date_due < today]
            total_overdue = sum(inv.amount_residual for inv in overdue_invs)
            
            partner.total_due_amount = total_due
            partner.total_overdue_amount = total_overdue
            
            if overdue_invs:
                max_days = max((today - inv.invoice_date_due).days for inv in overdue_invs)
                partner.max_days_overdue = max_days
            else:
                partner.max_days_overdue = 0

            # Compute Status
            if partner.latest_followup_level_id and partner.latest_followup_level_id.auto_credit_hold:
                partner.followup_status = 'on_hold'
            elif partner.next_followup_date and partner.next_followup_date <= today and total_overdue > 0:
                partner.followup_status = 'in_need_of_action'
            elif total_overdue > 0:
                partner.followup_status = 'with_overdue'
            else:
                partner.followup_status = 'no_action'

    def _search_followup_status(self, operator, value):
        # Allow searching by partner with overdue invoices
        today = fields.Date.context_today(self)
        if operator == '=' and value == 'with_overdue':
            overdue_moves = self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', today)
            ])
            return [('id', 'in', overdue_moves.mapped('partner_id.commercial_partner_id').ids)]
        return []

    def _get_applicable_followup_level(self, max_days, company):
        """Find the highest dunning level whose delay threshold is reached."""
        return self.env['account.followup.level'].search([
            ('company_id', '=', company.id),
            ('active', '=', True),
            ('delay', '<=', max_days)
        ], order='delay desc', limit=1)

    def action_trigger_manual_followup(self):
        """Open the manual follow-up workbench wizard."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Follow-up Workbench'),
            'res_model': 'account.followup.manual.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_total_overdue_amount': self.total_overdue_amount,
                'default_followup_level_id': self.latest_followup_level_id.id or False,
            }
        }

    def action_view_unpaid_invoices(self):
        """View list of unpaid customer invoices for this partner."""
        self.ensure_one()
        invoices = self._get_unpaid_customer_invoices()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['domain'] = [('id', 'in', invoices.ids)]
        action['context'] = {'default_move_type': 'out_invoice'}
        return action

    def action_view_followup_history(self):
        """View all audit history records for this partner."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Follow-up History: %s') % self.display_name,
            'res_model': 'account.followup.history',
            'view_mode': 'list,form',
            'domain': [('partner_id', '=', self.id)],
            'context': {'default_partner_id': self.id},
        }

    def action_print_statement_of_account(self):
        """Print formal Statement of Account & Overdue Notice PDF."""
        self.ensure_one()
        return self.env.ref('account_followup_dunning_hub.action_report_statement_of_account').report_action(self)

    @api.model
    def _cron_process_automated_followups(self):
        """Daily automated dunning cron job."""
        today = fields.Date.context_today(self)
        companies = self.env['res.company'].search([])

        for company in companies:
            # Find all overdue posted invoices for this company
            overdue_moves = self.env['account.move'].search([
                ('company_id', '=', company.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', today)
            ])
            partners = overdue_moves.mapped('partner_id.commercial_partner_id').filtered(
                lambda p: not p.exclude_from_followup
            )

            for partner in partners:
                # Check next follow-up date
                if partner.next_followup_date and partner.next_followup_date > today:
                    continue

                invoices = partner._get_unpaid_customer_invoices()
                overdue_invs = [inv for inv in invoices if inv.invoice_date_due and inv.invoice_date_due < today]
                if not overdue_invs:
                    continue

                max_days = max((today - inv.invoice_date_due).days for inv in overdue_invs)
                applicable_level = partner._get_applicable_followup_level(max_days, company)

                if not applicable_level:
                    continue

                total_overdue = sum(inv.amount_residual for inv in overdue_invs)

                # Send email if enabled
                if applicable_level.send_email and applicable_level.email_template_id and partner.email:
                    try:
                        applicable_level.email_template_id.send_mail(
                            partner.id,
                            force_send=True,
                            email_values={'email_to': partner.email}
                        )
                    except Exception:
                        pass

                # Record history audit
                self.env['account.followup.history'].create({
                    ('partner_id'): partner.id,
                    ('followup_level_id'): applicable_level.id,
                    ('action_date'): fields.Datetime.now(),
                    ('action_type'): 'cron',
                    ('currency_id'): partner.currency_id.id or company.currency_id.id,
                    ('total_overdue_amount'): total_overdue,
                    ('invoices_count'): len(overdue_invs),
                    ('notes'): _("Automated Dunning Trigger: %s (Max Overdue: %d Days, Overdue Amount: %s)") % (
                        applicable_level.name, max_days, total_overdue
                    ),
                    ('company_id'): company.id,
                })

                # Post to chatter
                partner.message_post(
                    body=_(
                        "<b>Automated Payment Follow-Up Executed</b><br/>"
                        "<b>Level:</b> %s<br/>"
                        "<b>Overdue Amount:</b> %s %s<br/>"
                        "<b>Overdue Invoices:</b> %d<br/>"
                        "<b>Max Days Overdue:</b> %d days"
                    ) % (
                        applicable_level.name,
                        total_overdue,
                        partner.currency_id.name or company.currency_id.name,
                        len(overdue_invs),
                        max_days
                    )
                )

                # Step forward next followup date (default 7 days)
                partner.write({
                    'latest_followup_level_id': applicable_level.id,
                    'latest_followup_date': today,
                    'next_followup_date': today + timedelta(days=7),
                })
