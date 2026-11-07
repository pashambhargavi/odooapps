# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    intercompany_auto_sync_enabled = fields.Boolean(
        string='Enable Inter-Company Automated Sync',
        default=True,
        help='Activate automatic reciprocal order and invoice generation for this company.'
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    intercompany_auto_sync_enabled = fields.Boolean(
        string='Enable Inter-Company Automated Sync',
        related='company_id.intercompany_auto_sync_enabled',
        readonly=False,
        help='Activate automatic reciprocal order and invoice generation for the active company.'
    )
