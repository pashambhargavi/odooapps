# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    apex_theme_config_id = fields.Many2one(
        'theme.apex.config',
        string="Active Apex Theme Configuration",
        compute='_compute_apex_theme_config',
        inverse='_inverse_apex_theme_config',
        readonly=False
    )

    apex_neon_preset = fields.Selection(
        related='apex_theme_config_id.neon_preset',
        string="Cyber Neon Preset",
        readonly=False
    )

    apex_neon_color = fields.Char(
        related='apex_theme_config_id.neon_color',
        string="Primary Neon Color",
        readonly=False
    )

    apex_glass_blur_strength = fields.Selection(
        related='apex_theme_config_id.glass_blur_strength',
        string="Glass Blur Level",
        readonly=False
    )

    apex_neon_glow_strength = fields.Selection(
        related='apex_theme_config_id.neon_glow_strength',
        string="Glow Intensity",
        readonly=False
    )

    apex_enable_glass_app_drawer = fields.Boolean(
        related='apex_theme_config_id.enable_glass_app_drawer',
        string="Frosted Glass App Switcher",
        readonly=False
    )

    apex_enable_glowing_inputs = fields.Boolean(
        related='apex_theme_config_id.enable_glowing_inputs',
        string="Glowing Input Focus Rings",
        readonly=False
    )

    apex_font_family = fields.Selection(
        related='apex_theme_config_id.font_family',
        string="Futuristic Typography",
        readonly=False
    )

    def _compute_apex_theme_config(self):
        for record in self:
            config = self.env['theme.apex.config'].search([
                ('company_id', '=', self.env.company.id),
                ('is_active', '=', True)
            ], limit=1)
            if not config:
                config = self.env['theme.apex.config'].search([('is_active', '=', True)], limit=1)
            record.apex_theme_config_id = config.id if config else False

    def _inverse_apex_theme_config(self):
        for record in self:
            if not record.apex_theme_config_id:
                config = self.env['theme.apex.config'].create({
                    'name': f"{self.env.company.name} Apex Cyber Profile",
                    'company_id': self.env.company.id,
                    'is_active': True,
                })
                record.apex_theme_config_id = config.id
