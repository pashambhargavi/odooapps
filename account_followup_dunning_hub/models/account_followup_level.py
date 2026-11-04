# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AccountFollowupLevel(models.Model):
    _name = 'account.followup.level'
    _description = 'Payment Follow-up & Dunning Level'
    _order = 'delay asc, sequence asc, id asc'

    name = fields.Char(string='Level Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    delay = fields.Integer(
        string='Overdue Delay (Days)',
        required=True,
        default=15,
        help='Number of days past invoice due date to trigger this follow-up escalation level.'
    )
    send_email = fields.Boolean(
        string='Automate Email Dispatch',
        default=True,
        help='When enabled, the automated cron will email the customer with the linked template.'
    )
    email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'res.partner')]",
        help='Template dispatched when this follow-up level triggers.'
    )
    auto_credit_hold = fields.Boolean(
        string='Trigger Credit Hold',
        default=False,
        help='If checked, customers reaching this level are flagged with a critical credit hold.'
    )
    description = fields.Text(
        string='Default Communication Body',
        help='Default text used in statements and reminder notices.'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    active = fields.Boolean(default=True)
