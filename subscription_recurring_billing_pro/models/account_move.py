# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one(
        'subscription.pro',
        string='Originating Subscription',
        copy=False,
        readonly=True,
        help='Reference to the recurring contract that generated this customer invoice.'
    )
