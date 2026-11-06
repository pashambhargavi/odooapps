# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    apex_neon_preset = fields.Selection([
        ('electric_cyan', 'Electric Cyan'),
        ('cyber_magenta', 'Cyber Magenta'),
        ('neon_emerald', 'Neon Emerald'),
        ('ultraviolet', 'Ultraviolet'),
        ('solar_gold', 'Solar Gold'),
    ], string="Personal Neon Mood", default='electric_cyan')

    apex_glow_enabled = fields.Boolean(string="Enable Neon Ambient Glow", default=True)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['apex_neon_preset', 'apex_glow_enabled']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['apex_neon_preset', 'apex_glow_enabled']

    @api.model
    def cycle_neon_mood(self):
        """1-click systray action cycling through neon moods."""
        moods = ['electric_cyan', 'cyber_magenta', 'neon_emerald', 'ultraviolet', 'solar_gold']
        current = self.env.user.apex_neon_preset or 'electric_cyan'
        next_idx = (moods.index(current) + 1) % len(moods) if current in moods else 0
        new_mood = moods[next_idx]
        self.env.user.sudo().write({'apex_neon_preset': new_mood})
        return {'new_mood': new_mood}
