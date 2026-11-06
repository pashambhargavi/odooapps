# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    theme_config_id = fields.Many2one(
        'theme.config',
        string="Active Theme Configuration",
        compute='_compute_theme_config',
        inverse='_inverse_theme_config',
        readonly=False
    )

    theme_layout_mode = fields.Selection(
        related='theme_config_id.layout_mode',
        string="Navigation Layout Style",
        readonly=False
    )

    theme_color_preset = fields.Selection(
        related='theme_config_id.color_preset',
        string="Color Palette Preset",
        readonly=False
    )

    theme_primary_color = fields.Char(
        related='theme_config_id.primary_color',
        string="Primary Brand Color",
        readonly=False
    )

    theme_accent_color = fields.Char(
        related='theme_config_id.accent_color',
        string="Accent Color",
        readonly=False
    )

    theme_navbar_bg_color = fields.Char(
        related='theme_config_id.navbar_bg_color',
        string="Top Navbar Color",
        readonly=False
    )

    theme_sidebar_bg_color = fields.Char(
        related='theme_config_id.sidebar_bg_color',
        string="Sidebar Background Color",
        readonly=False
    )

    theme_font_family = fields.Selection(
        related='theme_config_id.font_family',
        string="Typography / Font Family",
        readonly=False
    )

    theme_border_radius_size = fields.Selection(
        related='theme_config_id.border_radius_size',
        string="Border Radius / Corners",
        readonly=False
    )

    theme_enable_sticky_list_headers = fields.Boolean(
        related='theme_config_id.enable_sticky_list_headers',
        string="Sticky List Headers",
        readonly=False
    )

    theme_enable_sticky_form_statusbar = fields.Boolean(
        related='theme_config_id.enable_sticky_form_statusbar',
        string="Sticky Form Statusbar",
        readonly=False
    )

    theme_enable_list_zebra_striping = fields.Boolean(
        related='theme_config_id.enable_list_zebra_striping',
        string="List Zebra Striping",
        readonly=False
    )

    theme_login_template = fields.Selection(
        related='theme_config_id.login_template',
        string="Login Screen Template",
        readonly=False
    )

    theme_login_headline = fields.Char(
        related='theme_config_id.login_headline',
        string="Login Screen Headline",
        readonly=False
    )

    def _compute_theme_config(self):
        for record in self:
            config = self.env['theme.config'].search([
                ('company_id', '=', self.env.company.id),
                ('is_active', '=', True)
            ], limit=1)
            if not config:
                config = self.env['theme.config'].search([('is_active', '=', True)], limit=1)
            record.theme_config_id = config.id if config else False

    def _inverse_theme_config(self):
        for record in self:
            if not record.theme_config_id:
                config = self.env['theme.config'].create({
                    'name': f"{self.env.company.name} Theme Profile",
                    'company_id': self.env.company.id,
                    'is_active': True,
                })
                record.theme_config_id = config.id
