# -*- coding: utf-8 -*-
from odoo import models, fields, api
from .omni_theme_config import THEME_PRESETS, PALETTE_DEFAULTS


class ResUsers(models.Model):
    _inherit = 'res.users'

    omni_theme_selection = fields.Selection(
        selection=THEME_PRESETS,
        string='Active Workspace Theme',
        default='emerald_aurora',
        help='Personal choice of the 10 included OmniThemes.'
    )

    def action_switch_omni_theme(self, theme_key):
        """Called by Systray OWL component or RPC to switch theme instantly."""
        self.ensure_one()
        if theme_key in dict(THEME_PRESETS):
            self.sudo().write({'omni_theme_selection': theme_key})
            return {
                'success': True,
                'theme_key': theme_key,
                'palette': PALETTE_DEFAULTS.get(theme_key, {})
            }
        return {'success': False, 'error': 'Invalid theme key'}

    def action_cycle_omni_theme(self):
        """Cycles forward to the next theme in the 10-theme roster."""
        self.ensure_one()
        current = self.omni_theme_selection or 'emerald_aurora'
        keys = [k for k, _ in THEME_PRESETS]
        try:
            curr_idx = keys.index(current)
            next_idx = (curr_idx + 1) % len(keys)
        except ValueError:
            next_idx = 0
        next_key = keys[next_idx]
        self.sudo().write({'omni_theme_selection': next_key})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
