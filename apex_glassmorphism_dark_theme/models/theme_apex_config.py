# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ThemeApexConfig(models.Model):
    _name = 'theme.apex.config'
    _description = 'Apex Glassmorphism & Cyber Neon Theme Configuration'
    _check_company_auto = True

    name = fields.Char(string="Theme Profile Name", required=True, default="Apex Cyber Neon Profile")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)
    is_active = fields.Boolean(string="Active Theme", default=True)

    # Neon Color Presets
    neon_preset = fields.Selection([
        ('electric_cyan', 'Electric Cyber Cyan (#00F0FF)'),
        ('cyber_magenta', 'Cyberpunk Neon Magenta (#FF007F)'),
        ('neon_emerald', 'Matrix Neon Emerald (#10B981)'),
        ('ultraviolet', 'Ultraviolet Neon Glow (#8B5CF6)'),
        ('solar_gold', 'Solar Flare Amber Gold (#F59E0B)'),
        ('custom', 'Custom Cyber Neon Colors'),
    ], string="Neon Accent Preset", default='electric_cyan', required=True)

    neon_color = fields.Char(string="Primary Neon Color", default="#00F0FF", required=True)
    neon_glow_color = fields.Char(string="Neon Glow Shadow", default="rgba(0, 240, 255, 0.4)", required=True)
    glass_card_bg = fields.Char(string="Glass Card Background", default="rgba(15, 23, 42, 0.82)", required=True)
    glass_surface_border = fields.Char(string="Glass Border Color", default="rgba(0, 240, 255, 0.25)", required=True)

    # Glassmorphism Controls
    glass_blur_strength = fields.Selection([
        ('subtle_8px', 'Subtle Acrylic (8px Blur)'),
        ('frosted_16px', 'Standard Frosted Glass (16px Blur)'),
        ('deep_24px', 'Deep Liquid Glass (24px Blur)'),
    ], string="Glass Blur Level", default='frosted_16px', required=True)

    neon_glow_strength = fields.Selection([
        ('subtle', 'Subtle Edge Glow'),
        ('medium', 'Medium Luminous Glow'),
        ('intense', 'High-Intensity Cyber Glow'),
    ], string="Glow Intensity", default='medium', required=True)

    # UI Controls
    enable_glass_app_drawer = fields.Boolean(string="Frosted Glass App Switcher", default=True)
    enable_glowing_inputs = fields.Boolean(string="Glowing Input Focus Rings", default=True)
    enable_sticky_glass_headers = fields.Boolean(string="Sticky Glass Table Headers", default=True)
    enable_glass_dock_mobile = fields.Boolean(string="Mobile Floating Glass Dock", default=True)

    font_family = fields.Selection([
        ('outfit', 'Outfit (Futuristic & Geometric)'),
        ('inter', 'Inter (Modern High-Tech)'),
        ('roboto', 'Roboto (Standard Clean)'),
        ('system', 'System Default'),
    ], string="Futuristic Typography", default='outfit', required=True)

    login_headline = fields.Char(string="Login Portal Headline", default="Next-Generation Enterprise Intelligence")
    login_subtext = fields.Text(string="Login Subtext", default="Quantum-speed operations across Global Accounting, Inventory Logistics, and Multi-Tier Governance.")

    @api.onchange('neon_preset')
    def _onchange_neon_preset(self):
        presets = {
            'electric_cyan': {
                'neon': '#00F0FF',
                'glow': 'rgba(0, 240, 255, 0.4)',
                'bg': 'rgba(15, 23, 42, 0.85)',
                'border': 'rgba(0, 240, 255, 0.25)',
            },
            'cyber_magenta': {
                'neon': '#FF007F',
                'glow': 'rgba(255, 0, 127, 0.4)',
                'bg': 'rgba(24, 17, 36, 0.85)',
                'border': 'rgba(255, 0, 127, 0.25)',
            },
            'neon_emerald': {
                'neon': '#10B981',
                'glow': 'rgba(16, 185, 129, 0.4)',
                'bg': 'rgba(9, 26, 20, 0.85)',
                'border': 'rgba(16, 185, 129, 0.25)',
            },
            'ultraviolet': {
                'neon': '#8B5CF6',
                'glow': 'rgba(139, 92, 246, 0.4)',
                'bg': 'rgba(20, 16, 44, 0.85)',
                'border': 'rgba(139, 92, 246, 0.25)',
            },
            'solar_gold': {
                'neon': '#F59E0B',
                'glow': 'rgba(245, 158, 11, 0.4)',
                'bg': 'rgba(28, 24, 8, 0.85)',
                'border': 'rgba(245, 158, 11, 0.25)',
            },
        }
        if self.neon_preset in presets:
            d = presets[self.neon_preset]
            self.neon_color = d['neon']
            self.neon_glow_color = d['glow']
            self.glass_card_bg = d['bg']
            self.glass_surface_border = d['border']

    def action_apply_preset(self):
        self._onchange_neon_preset()
        return True

    @api.model
    def get_active_apex_config(self):
        config = self.search([('company_id', '=', self.env.company.id), ('is_active', '=', True)], limit=1)
        if not config:
            config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            return {
                'neon_color': '#00F0FF',
                'neon_glow_color': 'rgba(0, 240, 255, 0.4)',
                'glass_card_bg': 'rgba(15, 23, 42, 0.85)',
                'glass_surface_border': 'rgba(0, 240, 255, 0.25)',
                'glass_blur_strength': 'frosted_16px',
                'neon_glow_strength': 'medium',
                'font_family': 'outfit',
                'enable_glass_app_drawer': True,
                'enable_glowing_inputs': True,
                'enable_sticky_glass_headers': True,
                'enable_glass_dock_mobile': True,
            }
        return {
            'neon_color': config.neon_color,
            'neon_glow_color': config.neon_glow_color,
            'glass_card_bg': config.glass_card_bg,
            'glass_surface_border': config.glass_surface_border,
            'glass_blur_strength': config.glass_blur_strength,
            'neon_glow_strength': config.neon_glow_strength,
            'font_family': config.font_family,
            'enable_glass_app_drawer': config.enable_glass_app_drawer,
            'enable_glowing_inputs': config.enable_glowing_inputs,
            'enable_sticky_glass_headers': config.enable_sticky_glass_headers,
            'enable_glass_dock_mobile': config.enable_glass_dock_mobile,
        }
