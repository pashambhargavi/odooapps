# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    theme_dark_mode = fields.Selection([
        ('light', 'Light Mode'),
        ('dark', 'Dark Mode'),
        ('system', 'Sync with OS / Browser'),
    ], string="Theme Appearance", default='light',
       help="Select personal appearance mode. Can also be toggled directly from the top navigation bar.")

    theme_density = fields.Selection([
        ('comfortable', 'Comfortable (Standard Enterprise)'),
        ('compact', 'Compact (High Data Density)'),
        ('spacious', 'Spacious (Touch & Tablet Friendly)'),
    ], string="UI Density", default='comfortable')

    theme_sidebar_collapsed = fields.Boolean(string="Collapse Sidebar by Default", default=False)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ['theme_dark_mode', 'theme_density', 'theme_sidebar_collapsed']

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ['theme_dark_mode', 'theme_density', 'theme_sidebar_collapsed']

    @api.model
    def toggle_dark_mode(self):
        """1-click toggle between light and dark mode for current user from systray."""
        user = self.env.user
        new_mode = 'dark' if user.theme_dark_mode != 'dark' else 'light'
        user.sudo().write({'theme_dark_mode': new_mode})
        return {'new_mode': new_mode}
