# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    luxe_theme_config_id = fields.Many2one(
        'minimal.luxe.config',
        string="Active Minimal Luxe Profile",
        compute='_compute_luxe_theme_config',
        inverse='_inverse_luxe_theme_config',
        help="Active Minimal Luxe profile applied to the company."
    )

    luxe_theme_mode = fields.Selection(
        related='luxe_theme_config_id.theme_mode',
        readonly=False,
        string="Base Canvas Style"
    )

    luxe_luxury_accent = fields.Selection(
        related='luxe_theme_config_id.luxury_accent',
        readonly=False,
        string="Luxury Metal Accent"
    )

    luxe_zen_mode_enabled = fields.Boolean(
        related='luxe_theme_config_id.zen_mode_enabled',
        readonly=False,
        string="Zen Focus Mode"
    )

    luxe_hairline_border = fields.Boolean(
        related='luxe_theme_config_id.hairline_border',
        readonly=False,
        string="Hairline 1px Borders"
    )

    luxe_font_preset = fields.Selection(
        related='luxe_theme_config_id.font_preset',
        readonly=False,
        string="Typography Engine"
    )

    def _compute_luxe_theme_config(self):
        for record in self:
            config = self.env['minimal.luxe.config'].search([
                ('company_id', '=', self.env.company.id),
                ('is_active', '=', True)
            ], limit=1)
            record.luxe_theme_config_id = config.id if config else False

    def _inverse_luxe_theme_config(self):
        for record in self:
            if record.luxe_theme_config_id:
                record.luxe_theme_config_id.is_active = True
