# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    asset_auto_post_depreciation = fields.Boolean(
        string='Auto-Post Due Depreciation Schedules',
        config_parameter='account_asset_barcode_audit_pro.asset_auto_post_depreciation',
        default=True,
        help='Automatically post depreciation journal entries when the schedule date arrives.'
    )
    asset_strict_audit_mode = fields.Boolean(
        string='Strict Audit Verification Mode',
        config_parameter='account_asset_barcode_audit_pro.asset_strict_audit_mode',
        default=False,
        help='Require physical barcode/QR scan confirmation before permitting asset location or custodian changes.'
    )
