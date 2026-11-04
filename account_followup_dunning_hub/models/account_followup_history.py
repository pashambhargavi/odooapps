# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountFollowupHistory(models.Model):
    _name = 'account.followup.history'
    _description = 'Payment Follow-up Audit Trail'
    _order = 'action_date desc, id desc'

    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        ondelete='cascade',
        index=True
    )
    followup_level_id = fields.Many2one(
        'account.followup.level',
        string='Follow-up Level',
        ondelete='set null'
    )
    action_date = fields.Datetime(
        string='Action Date',
        default=fields.Datetime.now,
        required=True
    )
    action_type = fields.Selection([
        ('cron', 'Automated Cron Engine'),
        ('manual_email', 'Manual Email Dispatch'),
        ('phone', 'Phone Call Follow-up'),
        ('promise', 'Payment Promise Recorded'),
        ('letter', 'Printed Statement / Formal Notice'),
    ], string='Action Type', default='manual_email', required=True)

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )
    total_overdue_amount = fields.Monetary(
        string='Overdue Amount at Action',
        currency_field='currency_id'
    )
    invoices_count = fields.Integer(string='Overdue Invoices Count')
    promised_payment_date = fields.Date(string='Promised Payment Date')
    notes = fields.Text(string='Communication Notes & Promises')
    user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        default=lambda self: self.env.user
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
