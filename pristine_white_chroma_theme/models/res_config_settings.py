# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    chroma_theme_config_id = fields.Many2one(
        'chroma.theme.config',
        string="Active Pristine Chroma Profile",
        compute='_compute_chroma_theme_config',
        inverse='_inverse_chroma_theme_config',
        help="Active Pristine White Chroma profile applied to the company."
    )

    chroma_canvas_style = fields.Selection(
        related='chroma_theme_config_id.canvas_style',
        readonly=False,
        string="Canvas Background Mode"
    )

    chroma_preset = fields.Selection(
        related='chroma_theme_config_id.chroma_preset',
        readonly=False,
        string="Header & Button Color Preset"
    )

    chroma_header_bg = fields.Char(
        related='chroma_theme_config_id.header_bg',
        readonly=False,
        string="Vibrant Header Color"
    )

    chroma_button_shape = fields.Selection(
        related='chroma_theme_config_id.button_shape',
        readonly=False,
        string="Button Corner Geometry"
    )

    chroma_card_shadow = fields.Selection(
        related='chroma_theme_config_id.card_shadow',
        readonly=False,
        string="Card Elevation & Shadow"
    )

    def _compute_chroma_theme_config(self):
        for record in self:
            config = self.env['chroma.theme.config'].search([
                ('company_id', '=', self.env.company.id),
                ('is_active', '=', True)
            ], limit=1)
            record.chroma_theme_config_id = config.id if config else False

    def _inverse_chroma_theme_config(self):
        for record in self:
            if record.chroma_theme_config_id:
                record.chroma_theme_config_id.is_active = True
