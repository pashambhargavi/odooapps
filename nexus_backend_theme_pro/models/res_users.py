# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    nexus_chatter_position = fields.Selection([
        ('default', 'Use Company Theme Setting'),
        ('sided', 'Side-by-Side (Right Column Split)'),
        ('bottom', 'Bottom Stacked (Classic Odoo)'),
    ], string="Personal Chatter Placement", default='default',
       help="Override company default chatter placement on form views.")

    nexus_layout_mode = fields.Selection([
        ('default', 'Use Company Theme Setting'),
        ('sidebar', 'SaaS Collapsible Sidebar'),
        ('topbar', 'Enterprise Topbar'),
        ('minirail', 'Compact Mini-Rail'),
    ], string="Personal Navigation Layout", default='default',
       help="Override company default navigation layout.")

    nexus_table_density = fields.Selection([
        ('default', 'Use Company Theme Setting'),
        ('compact', 'Compact (High Density)'),
        ('standard', 'Standard ERP'),
        ('spacious', 'Spacious (Touch-Friendly)'),
    ], string="Personal Data Density", default='default')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'nexus_chatter_position', 'nexus_layout_mode', 'nexus_table_density'
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            'nexus_chatter_position', 'nexus_layout_mode', 'nexus_table_density'
        ]

    @api.model
    def toggle_chatter_position(self):
        """1-click toggle between side-by-side and bottom chatter from systray."""
        user = self.env.user
        current = user.nexus_chatter_position
        if current == 'sided':
            new_val = 'bottom'
        elif current == 'bottom':
            new_val = 'sided'
        else:
            # currently default, flip to opposite of company config
            config = self.env['nexus.theme.config'].get_active_nexus_config()
            new_val = 'bottom' if config.get('chatter_position') == 'sided' else 'sided'

        user.sudo().write({'nexus_chatter_position': new_val})
        return {'new_position': new_val}

    @api.model
    def cycle_layout_mode(self):
        """1-click cycle between sidebar -> topbar -> minirail -> sidebar."""
        user = self.env.user
        current = user.nexus_layout_mode
        cycle_order = ['sidebar', 'topbar', 'minirail']
        if current in cycle_order:
            idx = cycle_order.index(current)
            new_val = cycle_order[(idx + 1) % len(cycle_order)]
        else:
            new_val = 'topbar'

        user.sudo().write({'nexus_layout_mode': new_val})
        return {'new_layout': new_val}

    @api.model
    def toggle_table_density(self):
        """1-click cycle between compact -> standard -> spacious -> compact."""
        user = self.env.user
        current = user.nexus_table_density
        cycle_order = ['compact', 'standard', 'spacious']
        if current in cycle_order:
            idx = cycle_order.index(current)
            new_val = cycle_order[(idx + 1) % len(cycle_order)]
        else:
            new_val = 'compact'

        user.sudo().write({'nexus_table_density': new_val})
        return {'new_density': new_val}
