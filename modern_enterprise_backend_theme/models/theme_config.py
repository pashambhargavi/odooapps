# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ThemeConfig(models.Model):
    _name = 'theme.config'
    _description = 'NextGen Enterprise Theme Configuration'
    _check_company_auto = True

    name = fields.Char(string="Theme Profile Name", required=True, default="Default Enterprise Profile")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    is_active = fields.Boolean(string="Active Theme", default=True)

    # 1. Layout Architecture
    layout_mode = fields.Selection([
        ('enterprise_top', 'Enterprise Topbar with Fullscreen App Switcher'),
        ('modern_sidebar', 'Modern Left Collapsible Sidebar'),
        ('hybrid', 'Hybrid Topbar & Floating Drawer'),
    ], string="Navigation Layout Style", default='enterprise_top', required=True,
       help="Enterprise Topbar renders the native full-screen app grid; Modern Sidebar renders a collapsible left panel.")

    # 2. Color Palettes & Brand Identity
    color_preset = fields.Selection([
        ('enterprise_violet', 'Enterprise Signature Violet (#714B67)'),
        ('executive_navy', 'Executive Deep Navy (#0F172A)'),
        ('emerald_tech', 'Emerald Tech Green (#065F46)'),
        ('sapphire_blue', 'Sapphire Enterprise Blue (#1E40AF)'),
        ('crimson_luxury', 'Crimson Corporate Burgundy (#881337)'),
        ('dark_slate', 'Cyber Dark Slate (#18181B)'),
        ('custom', 'Custom Brand Colors'),
    ], string="Color Palette Preset", default='executive_navy', required=True)

    primary_color = fields.Char(string="Primary Brand Color", default="#0F172A", required=True)
    accent_color = fields.Char(string="Accent / Button Color", default="#2563EB", required=True)
    navbar_bg_color = fields.Char(string="Top Navbar Color", default="#0F172A", required=True)
    sidebar_bg_color = fields.Char(string="Sidebar Background Color", default="#1E293B", required=True)
    active_item_color = fields.Char(string="Active Menu Item Color", default="#38BDF8", required=True)

    # 3. Typography & Styling
    font_family = fields.Selection([
        ('system', 'System Default (San Francisco, Segoe UI, Roboto)'),
        ('inter', 'Inter (Modern SaaS & Clean Typography)'),
        ('roboto', 'Roboto (Standard Enterprise Material)'),
        ('poppins', 'Poppins (Geometric & Contemporary)'),
        ('open_sans', 'Open Sans (Balanced & High Legibility)'),
    ], string="Font Family", default='inter', required=True)

    border_radius_size = fields.Selection([
        ('sharp', 'Sharp Corporate (0px)'),
        ('subtle', 'Subtle Rounded (4px)'),
        ('modern', 'Modern Rounded (8px)'),
        ('smooth', 'Smooth Curved (12px)'),
    ], string="Corner Radius Style", default='modern', required=True)

    # 4. View Enhancements
    enable_sticky_list_headers = fields.Boolean(string="Sticky List Headers", default=True,
                                                help="Keeps table headers visible when scrolling through large records.")
    enable_sticky_form_statusbar = fields.Boolean(string="Sticky Form Statusbar", default=True,
                                                  help="Locks the action buttons and statusbar at the top of form views.")
    enable_list_zebra_striping = fields.Boolean(string="List View Zebra Striping", default=True,
                                                help="Alternating row colors for high readability on wide data grids.")

    # 5. Login Screen Styling
    login_template = fields.Selection([
        ('modern_split', 'Executive Split Screen with Brand Banner'),
        ('centered_card', 'Minimalist Centered Glass Card'),
        ('standard_odoo', 'Standard Odoo Layout with Theme Colors'),
    ], string="Login Screen Template", default='modern_split', required=True)

    login_headline = fields.Char(string="Login Screen Headline", default="Welcome to Your Enterprise Workspace")
    login_subtext = fields.Text(string="Login Subtext", default="Access your unified ERP, CRM, Inventory and Accounting operations securely.")

    @api.onchange('color_preset')
    def _onchange_color_preset(self):
        presets = {
            'enterprise_violet': {'primary': '#714B67', 'accent': '#00A09D', 'navbar': '#714B67', 'sidebar': '#56394F', 'active': '#00D1CE'},
            'executive_navy': {'primary': '#0F172A', 'accent': '#2563EB', 'navbar': '#0F172A', 'sidebar': '#1E293B', 'active': '#38BDF8'},
            'emerald_tech': {'primary': '#065F46', 'accent': '#059669', 'navbar': '#065F46', 'sidebar': '#047857', 'active': '#34D399'},
            'sapphire_blue': {'primary': '#1E40AF', 'accent': '#0284C7', 'navbar': '#1E40AF', 'sidebar': '#1E3A8A', 'active': '#60A5FA'},
            'crimson_luxury': {'primary': '#881337', 'accent': '#E11D48', 'navbar': '#881337', 'sidebar': '#4C0519', 'active': '#FB7185'},
            'dark_slate': {'primary': '#18181B', 'accent': '#6366F1', 'navbar': '#18181B', 'sidebar': '#27272A', 'active': '#A5B4FC'},
        }
        if self.color_preset in presets:
            data = presets[self.color_preset]
            self.primary_color = data['primary']
            self.accent_color = data['accent']
            self.navbar_bg_color = data['navbar']
            self.sidebar_bg_color = data['sidebar']
            self.active_item_color = data['active']

    def action_apply_preset(self):
        """Re-applies the preset colors explicitly."""
        self._onchange_color_preset()
        return True

    @api.model
    def get_active_theme_config(self):
        """Retrieves active company theme values as a dictionary for the webclient service."""
        config = self.search([('company_id', '=', self.env.company.id), ('is_active', '=', True)], limit=1)
        if not config:
            config = self.search([('is_active', '=', True)], limit=1)
        
        if not config:
            return {
                'layout_mode': 'enterprise_top',
                'primary_color': '#0F172A',
                'accent_color': '#2563EB',
                'navbar_bg_color': '#0F172A',
                'sidebar_bg_color': '#1E293B',
                'active_item_color': '#38BDF8',
                'font_family': 'inter',
                'border_radius_size': 'modern',
                'enable_sticky_list_headers': True,
                'enable_sticky_form_statusbar': True,
                'enable_list_zebra_striping': True,
                'login_template': 'modern_split',
            }
        
        return {
            'layout_mode': config.layout_mode,
            'primary_color': config.primary_color,
            'accent_color': config.accent_color,
            'navbar_bg_color': config.navbar_bg_color,
            'sidebar_bg_color': config.sidebar_bg_color,
            'active_item_color': config.active_item_color,
            'font_family': config.font_family,
            'border_radius_size': config.border_radius_size,
            'enable_sticky_list_headers': config.enable_sticky_list_headers,
            'enable_sticky_form_statusbar': config.enable_sticky_form_statusbar,
            'enable_list_zebra_striping': config.enable_list_zebra_striping,
            'login_template': config.login_template,
        }
