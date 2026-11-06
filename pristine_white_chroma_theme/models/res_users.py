# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    chroma_personal_preset = fields.Selection([
        ('default', 'Use Company Default Header Color'),
        ('royal_indigo', 'Electric Royal Indigo (#4F46E5)'),
        ('sunset_coral', 'Vibrant Sunset Coral (#EA580C)'),
        ('emerald_mint', 'Emerald Mint Tech (#059669)'),
        ('hyper_violet', 'Hyper Berry Violet (#7C3AED)'),
        ('ocean_cyan', 'Deep Ocean Cyan (#0284C7)'),
        ('ruby_rose', 'Ruby Rose Executive (#E11D48)'),
    ], string="Personal Header & Button Color", default='default',
       help="Personal vibrant header and action button color.")

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['chroma_personal_preset']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['chroma_personal_preset']

    @api.model
    def cycle_chroma_preset(self):
        """1-click cycle through vibrant header and button chromatic presets."""
        user = self.env.user
        current = user.chroma_personal_preset
        presets = ['royal_indigo', 'sunset_coral', 'emerald_mint', 'hyper_violet', 'ocean_cyan', 'ruby_rose']
        if current in presets:
            idx = presets.index(current)
            new_val = presets[(idx + 1) % len(presets)]
        else:
            new_val = 'royal_indigo'

        user.sudo().write({'chroma_personal_preset': new_val})
        from .chroma_theme_config import CHROMA_PRESETS
        return {
            'new_preset': new_val,
            'header_bg': CHROMA_PRESETS[new_val]['header'],
            'accent_color': CHROMA_PRESETS[new_val]['accent'],
        }
