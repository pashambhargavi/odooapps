# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    luxe_zen_mode = fields.Boolean(
        string="Zen Focus Mode Active",
        default=False,
        help="Fade non-essential navigation bars and focus entirely on the current workspace document."
    )

    luxe_personal_accent = fields.Selection([
        ('default', 'Use Company Luxury Accent'),
        ('sovereign_gold', '24K Sovereign Gold'),
        ('titanium', 'Pure Titanium Monochrome'),
        ('platinum_ice', 'Platinum Ice'),
        ('emerald_mint', 'Emerald Mint'),
        ('rose_gold', 'Rose Gold Luxury'),
    ], string="Personal Luxury Accent", default='default')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['luxe_zen_mode', 'luxe_personal_accent']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['luxe_zen_mode', 'luxe_personal_accent']

    @api.model
    def toggle_zen_mode(self):
        """1-click toggle for Zen Focus Mode from top systray."""
        user = self.env.user
        new_state = not user.luxe_zen_mode
        user.sudo().write({'luxe_zen_mode': new_state})
        return {'zen_mode_active': new_state}

    @api.model
    def cycle_luxury_accent(self):
        """1-click cycle through luxury metal accents."""
        user = self.env.user
        current = user.luxe_personal_accent
        accents = ['sovereign_gold', 'titanium', 'platinum_ice', 'emerald_mint', 'rose_gold']
        if current in accents:
            idx = accents.index(current)
            new_val = accents[(idx + 1) % len(accents)]
        else:
            new_val = 'sovereign_gold'

        user.sudo().write({'luxe_personal_accent': new_val})
        from .minimal_luxe_config import LUXE_ACCENTS
        return {
            'new_accent': new_val,
            'accent_hex': LUXE_ACCENTS[new_val]['accent']
        }
