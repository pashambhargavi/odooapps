# -*- coding: utf-8 -*-
from odoo import models, fields, api

LUXE_ACCENTS = {
    'titanium': {'accent': '#71717A', 'subtle': '#27272A'},
    'sovereign_gold': {'accent': '#D97706', 'subtle': '#451A03'},
    'platinum_ice': {'accent': '#38BDF8', 'subtle': '#0C4A6E'},
    'emerald_mint': {'accent': '#10B981', 'subtle': '#064E3B'},
    'rose_gold': {'accent': '#FB7185', 'subtle': '#4C0519'},
}

class MinimalLuxeConfig(models.Model):
    _name = 'minimal.luxe.config'
    _description = 'Minimal Luxe Theme & Zen Studio Configuration'

    name = fields.Char(string="Theme Profile Name", required=True, default="Minimal Luxe Obsidian")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    is_active = fields.Boolean(string="Active Theme Profile", default=True)

    # Monochromatic Canvas
    theme_mode = fields.Selection([
        ('obsidian_dark', 'Obsidian Black (#09090B - Linear OLED)'),
        ('chalk_light', 'Chalk White (#FAFAFA - High-Fashion Clean)'),
        ('warm_zinc', 'Studio Zinc (#18181B - Balanced Contrast)'),
    ], string="Base Surface Canvas", default='obsidian_dark', required=True)

    # Luxury Metal Accents
    luxury_accent = fields.Selection([
        ('sovereign_gold', '24K Sovereign Gold (#D97706)'),
        ('titanium', 'Pure Titanium Monochrome (#71717A)'),
        ('platinum_ice', 'Platinum Ice (#38BDF8)'),
        ('emerald_mint', 'Emerald Mint (#10B981)'),
        ('rose_gold', 'Rose Gold Luxury (#FB7185)'),
    ], string="Luxury Accent Color", default='sovereign_gold', required=True)

    accent_hex = fields.Char(string="Active Accent HEX", default='#D97706', required=True)

    # Zen Focus Mode
    zen_mode_enabled = fields.Boolean(string="Enable Zen Focus Mode", default=True,
                                      help="Allows users to fade out all sidebars and distractions with 1 click.")

    # Hairline Precision Borders
    hairline_border = fields.Boolean(string="Hairline 1px Precision Borders", default=True,
                                     help="Renders crisp 1px borders inspired by Linear and Apple interfaces.")

    # Typography Suite
    font_preset = fields.Selection([
        ('inter_jetbrains', 'Inter (Headings) + JetBrains Mono (Numbers & Ledgers)'),
        ('geist_mono', 'Geist & Monospace High-Density'),
        ('system_sans', 'Apple / SF Pro Native'),
    ], string="Typography Suite", default='inter_jetbrains', required=True)

    @api.onchange('luxury_accent')
    def _onchange_luxury_accent(self):
        if self.luxury_accent and self.luxury_accent in LUXE_ACCENTS:
            self.accent_hex = LUXE_ACCENTS[self.luxury_accent]['accent']

    def action_apply_accent(self):
        self.ensure_one()
        self._onchange_luxury_accent()
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
    def get_active_luxe_config(self):
        company = self.env.company
        config = self.search([
            ('company_id', '=', company.id),
            ('is_active', '=', True)
        ], limit=1)
        if not config:
            config = self.search([('is_active', '=', True)], limit=1)

        user = self.env.user
        user_zen = getattr(user, 'luxe_zen_mode', False)
        user_accent = getattr(user, 'luxe_personal_accent', 'default')

        eff_accent = LUXE_ACCENTS[user_accent]['accent'] if (user_accent and user_accent != 'default' and user_accent in LUXE_ACCENTS) else (config.accent_hex if config else '#D97706')

        if config:
            return {
                'id': config.id,
                'name': config.name,
                'theme_mode': config.theme_mode,
                'luxury_accent': config.luxury_accent,
                'accent_hex': eff_accent,
                'zen_mode_enabled': config.zen_mode_enabled,
                'zen_mode_active': user_zen,
                'hairline_border': config.hairline_border,
                'font_preset': config.font_preset,
            }
        return {
            'theme_mode': 'obsidian_dark',
            'luxury_accent': 'sovereign_gold',
            'accent_hex': eff_accent,
            'zen_mode_enabled': True,
            'zen_mode_active': user_zen,
            'hairline_border': True,
            'font_preset': 'inter_jetbrains',
        }
