# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_landed_cost_journal_id = fields.Many2one(
        'account.journal',
        string='Default Landed Cost Journal',
        related='company_id.landed_cost_journal_id',
        readonly=False,
        help='Default general journal for landed cost valuation entries.'
    )


class ResCompany(models.Model):
    _inherit = 'res.company'

    landed_cost_journal_id = fields.Many2one(
        'account.journal',
        string='Landed Cost Journal'
    )
