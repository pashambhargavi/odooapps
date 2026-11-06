# -*- coding: utf-8 -*-
from odoo import models, fields, api

PRESET_COLORS = {
    'sapphire': {'primary': '#1E40AF', 'accent': '#3B82F6', 'sidebar': '#0F172A', 'header': '#1E293B'},
    'emerald': {'primary': '#065F46', 'accent': '#10B981', 'sidebar': '#064E3B', 'header': '#047857'},
    'amethyst': {'primary': '#581C87', 'accent': '#8B5CF6', 'sidebar': '#3B0764', 'header': '#6B21A8'},
    'oled_dark': {'primary': '#06B6D4', 'accent': '#00F0FF', 'sidebar': '#050811', 'header': '#0B1322'},
    'crimson': {'primary': '#991B1B', 'accent': '#EF4444', 'sidebar': '#450A0A', 'header': '#7F1D1D'},
    'nordic': {'primary': '#334155', 'accent': '#64748B', 'sidebar': '#1E293B', 'header': '#0F172A'},
}

class NexusThemeConfig(models.Model):
    _name = 'nexus.theme.config'
    _description = 'Nexus Pro Backend Theme Configuration & Studio'

    name = fields.Char(string="Theme Profile Name", required=True, default="Nexus Pro Corporate Suite")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    is_active = fields.Boolean(string="Active Theme Profile", default=True,
                               help="Enable this profile as the default styling for the selected company.")

    # 3-in-1 Adaptive Navigation Layouts
    layout_mode = fields.Selection([
        ('sidebar', 'SaaS Collapsible Sidebar (Left Rail)'),
        ('topbar', 'Enterprise Topbar (Classic Header)'),
        ('minirail', 'Compact Mini-Rail (Slim 60px Icons)'),
    ], string="Navigation Layout Mode", default='sidebar', required=True,
       help="Choose how application menus and navigation bars are structured.")

    # Smart Chatter Position
    chatter_position = fields.Selection([
        ('sided', 'Side-by-Side (Right Column Split)'),
        ('bottom', 'Bottom Stacked (Classic Odoo)'),
    ], string="Chatter Box Placement", default='sided', required=True,
       help="Select whether chatter messages appear on the right side of forms or stacked beneath them.")

    # Data Density Modes
    table_density = fields.Selection([
        ('compact', 'Compact Density (Financial Ledgers & High Volume)'),
        ('standard', 'Standard ERP Density (Balanced UX)'),
        ('spacious', 'Spacious Density (Touch & Tablet Optimized)'),
    ], string="List & Table Density", default='standard', required=True,
       help="Controls vertical row padding in list views, kanban grids, and accounting registers.")

    # 6 Curated Color Presets
    color_preset = fields.Selection([
        ('sapphire', 'Royal Sapphire Corporate (Deep Blue)'),
        ('emerald', 'FinTech Emerald Wealth (Tech Green)'),
        ('amethyst', 'Imperial Amethyst Luxury (Executive Purple)'),
        ('oled_dark', 'Cyberpunk OLED Dark (Neon Cyan & Slate)'),
        ('crimson', 'Crimson Titan High-Energy (Corporate Red)'),
        ('nordic', 'Nordic Slate Minimalist (Steel Grey)'),
        ('custom', 'Custom Corporate Palette (Hex Codes)'),
    ], string="Color Palette Preset", default='sapphire', required=True)

    primary_color = fields.Char(string="Brand Primary Color", default='#1E40AF', required=True)
    accent_color = fields.Char(string="Brand Accent Color", default='#3B82F6', required=True)
    sidebar_bg = fields.Char(string="Sidebar Background Color", default='#0F172A', required=True)
    header_bg = fields.Char(string="Header / Systray Background", default='#1E293B', required=True)

    border_radius = fields.Selection([
        ('none', 'Square Minimalist (0px)'),
        ('small', 'Subtle Rounded (4px)'),
        ('medium', 'Modern Rounded (8px - Default)'),
        ('large', 'Organic Pill (14px)'),
    ], string="Card & Button Corner Radius", default='medium')

    sticky_header = fields.Boolean(string="Sticky Table Column Headers", default=True,
                                   help="Keep table headers visible when scrolling large records.")
    sticky_chatter = fields.Boolean(string="Sticky Form Chatter", default=True,
                                    help="Pin chatter box to viewport when scrolling long form views.")

    font_family = fields.Selection([
        ('inter', 'Inter / System Modern Sans'),
        ('roboto', 'Roboto Dense & Clear'),
        ('outfit', 'Outfit High-Tech Geometric'),
        ('poppins', 'Poppins Friendly Corporate'),
    ], string="Typography Suite", default='inter', required=True)

    @api.onchange('color_preset')
    def _onchange_color_preset(self):
        if self.color_preset and self.color_preset in PRESET_COLORS:
            preset = PRESET_COLORS[self.color_preset]
            self.primary_color = preset['primary']
            self.accent_color = preset['accent']
            self.sidebar_bg = preset['sidebar']
            self.header_bg = preset['header']

    def action_apply_preset(self):
        self.ensure_one()
        self._onchange_color_preset()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.is_active:
                self.search([
                    ('id', '!=', rec.id),
                    ('company_id', '=', rec.company_id.id),
                    ('is_active', '=', True)
                ]).write({'is_active': False})
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_active'):
            for rec in self:
                if rec.is_active:
                    self.search([
                        ('id', '!=', rec.id),
                        ('company_id', '=', rec.company_id.id),
                        ('is_active', '=', True)
                    ]).write({'is_active': False})
        return res

    @api.model
    def get_active_nexus_config(self):
        """Returns the active configuration dictionary for frontend services."""
        company = self.env.company
        config = self.search([
            ('company_id', '=', company.id),
            ('is_active', '=', True)
        ], limit=1)
        if not config:
            config = self.search([('is_active', '=', True)], limit=1)

        user = self.env.user
        # Allow user override for chatter and layout if configured
        user_chatter = getattr(user, 'nexus_chatter_position', 'default')
        user_layout = getattr(user, 'nexus_layout_mode', 'default')
        user_density = getattr(user, 'nexus_table_density', 'default')

        eff_chatter = user_chatter if user_chatter and user_chatter != 'default' else (config.chatter_position if config else 'sided')
        eff_layout = user_layout if user_layout and user_layout != 'default' else (config.layout_mode if config else 'sidebar')
        eff_density = user_density if user_density and user_density != 'default' else (config.table_density if config else 'standard')

        if config:
            return {
                'id': config.id,
                'name': config.name,
                'layout_mode': eff_layout,
                'chatter_position': eff_chatter,
                'table_density': eff_density,
                'color_preset': config.color_preset,
                'primary_color': config.primary_color,
                'accent_color': config.accent_color,
                'sidebar_bg': config.sidebar_bg,
                'header_bg': config.header_bg,
                'border_radius': config.border_radius,
                'sticky_header': config.sticky_header,
                'sticky_chatter': config.sticky_chatter,
                'font_family': config.font_family,
            }
        return {
            'layout_mode': eff_layout,
            'chatter_position': eff_chatter,
            'table_density': eff_density,
            'primary_color': '#1E40AF',
            'accent_color': '#3B82F6',
            'sidebar_bg': '#0F172A',
            'header_bg': '#1E293B',
            'border_radius': 'medium',
            'sticky_header': True,
            'sticky_chatter': True,
            'font_family': 'inter',
        }
