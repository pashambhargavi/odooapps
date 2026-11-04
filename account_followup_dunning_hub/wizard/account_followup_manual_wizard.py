# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountFollowupManualWizard(models.TransientModel):
    _name = 'account.followup.manual.wizard'
    _description = 'Manual Customer Follow-Up Workbench'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True
    )
    followup_level_id = fields.Many2one(
        'account.followup.level',
        string='Dunning Level',
        domain="[('company_id', '=', company_id)]"
    )
    action_type = fields.Selection([
        ('manual_email', 'Send Follow-up Email'),
        ('phone', 'Log Phone Call Discussion'),
        ('promise', 'Record Customer Payment Promise'),
        ('letter', 'Generate Printed Statement Notice'),
    ], string='Action Taken', default='manual_email', required=True)

    send_email = fields.Boolean(string='Send Email to Customer', default=True)
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'res.partner')]"
    )
    promised_payment_date = fields.Date(string='Promised Payment Date')
    next_followup_date = fields.Date(
        string='Next Action Date',
        default=lambda self: fields.Date.context_today(self) + timedelta(days=7),
        required=True
    )
    notes = fields.Text(
        string='Communication Notes / Agreements',
        help='Summarize the discussion, promise, or justification.'
    )
    total_overdue_amount = fields.Monetary(
        string='Overdue Amount',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    @api.onchange('followup_level_id')
    def _onchange_followup_level_id(self):
        if self.followup_level_id:
            self.email_template_id = self.followup_level_id.email_template_id
            if self.followup_level_id.description and not self.notes:
                self.notes = self.followup_level_id.description

    def action_confirm(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        partner = self.partner_id

        # Calculate overdue invoices count
        invoices = partner._get_unpaid_customer_invoices()
        overdue_invs = [inv for inv in invoices if inv.invoice_date_due and inv.invoice_date_due < today]

        # Dispatch email if requested
        if self.action_type == 'manual_email' and self.send_email:
            if not partner.email:
                raise UserError(_("Customer '%s' does not have a configured email address.") % partner.name)
            if self.email_template_id:
                self.email_template_id.send_mail(
                    partner.id,
                    force_send=True,
                    email_values={'email_to': partner.email}
                )

        # Create history record
        self.env['account.followup.history'].create({
            'partner_id': partner.id,
            'followup_level_id': self.followup_level_id.id or False,
            'action_date': fields.Datetime.now(),
            'action_type': self.action_type,
            'currency_id': self.currency_id.id,
            'total_overdue_amount': self.total_overdue_amount or partner.total_overdue_amount,
            'invoices_count': len(overdue_invs),
            'promised_payment_date': self.promised_payment_date,
            'notes': self.notes,
            'user_id': self.env.user.id,
            'company_id': self.company_id.id,
        })

        # Update partner
        vals = {
            'latest_followup_date': today,
            'next_followup_date': self.next_followup_date,
        }
        if self.followup_level_id:
            vals['latest_followup_level_id'] = self.followup_level_id.id
        partner.write(vals)

        # Post chatter note
        action_labels = dict(self._fields['action_type'].selection)
        body = _(
            "<b>Payment Follow-Up Action Logged</b><br/>"
            "<b>Action:</b> %s<br/>"
            "<b>Level:</b> %s<br/>"
            "<b>Overdue Amount:</b> %s %s<br/>"
            "<b>Next Follow-up Scheduled:</b> %s<br/>"
        ) % (
            action_labels.get(self.action_type, self.action_type),
            self.followup_level_id.name if self.followup_level_id else _('Unassigned'),
            self.total_overdue_amount or partner.total_overdue_amount,
            self.currency_id.name,
            self.next_followup_date
        )
        if self.promised_payment_date:
            body += _("<br/><b>Promised Payment Date:</b> %s") % self.promised_payment_date
        if self.notes:
            body += _("<br/><b>Notes:</b> %s") % self.notes

        partner.message_post(body=body)

        # If letter requested, return report action
        if self.action_type == 'letter':
            return partner.action_print_statement_of_account()

        return {'type': 'ir.actions.act_window_close'}
