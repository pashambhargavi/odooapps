# -*- coding: utf-8 -*-
from odoo import models, fields, api

CHROMA_PRESETS = {
    'royal_indigo': {'header': '#4F46E5', 'accent': '#6366F1', 'button_text': '#FFFFFF'},
    'sunset_coral': {'header': '#EA580C', 'accent': '#F97316', 'button_text': '#FFFFFF'},
    'emerald_mint': {'header': '#059669', 'accent': '#10B981', 'button_text': '#FFFFFF'},
    'hyper_violet': {'header': '#7C3AED', 'accent': '#8B5CF6', 'button_text': '#FFFFFF'},
    'ocean_cyan': {'header': '#0284C7', 'accent': '#0EA5E9', 'button_text': '#FFFFFF'},
    'ruby_rose': {'header': '#E11D48', 'accent': '#F43F5E', 'button_text': '#FFFFFF'},
}

class ChromaThemeConfig(models.Model):
    _name = 'chroma.theme.config'
    _description = 'Pristine White Canvas & Chroma Header Theme Configuration'

    name = fields.Char(string="Theme Profile Name", required=True, default="Pristine White Royal Indigo")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    is_active = fields.Boolean(string="Active Theme Profile", default=True)

    # 100% Pure White Canvas Styling
    canvas_style = fields.Selection([
        ('pure_white', '100% Pure Crisp White (#FFFFFF Paper-Like Canvas)'),
        ('soft_paper', 'Soft Linen White (#FAFAFA High-End Warm White)'),
    ], string="Canvas Background Mode", default='pure_white', required=True,
       help="Ensures all form views, list tables, kanban stages and dialogs are pristine clean white.")

    # Vibrant Header & Button Color Engine
    chroma_preset = fields.Selection([
        ('royal_indigo', 'Electric Royal Indigo (#4F46E5)'),
        ('sunset_coral', 'Vibrant Sunset Coral (#EA580C)'),
        ('emerald_mint', 'Emerald Mint Tech (#059669)'),
        ('hyper_violet', 'Hyper Berry Violet (#7C3AED)'),
        ('ocean_cyan', 'Deep Ocean Cyan (#0284C7)'),
        ('ruby_rose', 'Ruby Rose Executive (#E11D48)'),
        ('custom', 'Custom Chromatic Color'),
    ], string="Header & Button Color Preset", default='royal_indigo', required=True)

    header_bg = fields.Char(string="Vibrant Header Color", default='#4F46E5', required=True)
    accent_color = fields.Char(string="Interactive Accent & Glow", default='#6366F1', required=True)

    button_shape = fields.Selection([
        ('modern', 'Modern Rounded (8px - Default)'),
        ('pill', 'Curved Pill Rounded (20px)'),
        ('sharp', 'Sharp Precision (4px)'),
    ], string="Button Corner Geometry", default='modern', required=True)

    card_shadow = fields.Selection([
        ('soft', 'Soft Subtle Elevation (0 4px 16px rgba(0,0,0,0.04))'),
        ('crisp', 'Crisp 1px Border Elevation (#E2E8F0)'),
        ('floating', 'Deep Floating Paper (0 10px 25px rgba(0,0,0,0.06))'),
    ], string="White Card Elevation & Shadow", default='soft', required=True)

    sticky_header = fields.Boolean(string="Sticky Navbar & Control Panel", default=True)

    font_family = fields.Selection([
        ('inter', 'Inter / System High-Contrast Sans'),
        ('plus_jakarta', 'Plus Jakarta Modern Sans'),
        ('outfit', 'Outfit Executive Geometric'),
    ], string="Typography Suite", default='inter', required=True)

    @api.onchange('chroma_preset')
    def _onchange_chroma_preset(self):
        if self.chroma_preset and self.chroma_preset in CHROMA_PRESETS:
            preset = CHROMA_PRESETS[self.chroma_preset]
            self.header_bg = preset['header']
            self.accent_color = preset['accent']

    def action_apply_preset(self):
        self.ensure_one()
        self._onchange_chroma_preset()
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
    def get_active_chroma_config(self):
        company = self.env.company
        config = self.search([
            ('company_id', '=', company.id),
            ('is_active', '=', True)
        ], limit=1)
        if not config:
            config = self.search([('is_active', '=', True)], limit=1)

        user = self.env.user
        user_preset = getattr(user, 'chroma_personal_preset', 'default')

        eff_header = CHROMA_PRESETS[user_preset]['header'] if (user_preset and user_preset != 'default' and user_preset in CHROMA_PRESETS) else (config.header_bg if config else '#4F46E5')
        eff_accent = CHROMA_PRESETS[user_preset]['accent'] if (user_preset and user_preset != 'default' and user_preset in CHROMA_PRESETS) else (config.accent_color if config else '#6366F1')

        if config:
            return {
                'id': config.id,
                'name': config.name,
                'canvas_style': config.canvas_style,
                'chroma_preset': config.chroma_preset,
                'header_bg': eff_header,
                'accent_color': eff_accent,
                'button_shape': config.button_shape,
                'card_shadow': config.card_shadow,
                'sticky_header': config.sticky_header,
                'font_family': config.font_family,
            }
        return {
            'canvas_style': 'pure_white',
            'chroma_preset': 'royal_indigo',
            'header_bg': eff_header,
            'accent_color': eff_accent,
            'button_shape': 'modern',
            'card_shadow': 'soft',
            'sticky_header': True,
            'font_family': 'inter',
        }
