# -*- coding: utf-8 -*-
from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    nexus_theme_config_id = fields.Many2one(
        'nexus.theme.config',
        string="Active Nexus Theme Profile",
        compute='_compute_nexus_theme_config',
        inverse='_inverse_nexus_theme_config',
        help="The active Nexus Pro theme profile applied to the current company."
    )

    nexus_layout_mode = fields.Selection(
        related='nexus_theme_config_id.layout_mode',
        readonly=False,
        string="Default Navigation Layout"
    )

    nexus_chatter_position = fields.Selection(
        related='nexus_theme_config_id.chatter_position',
        readonly=False,
        string="Default Chatter Placement"
    )

    nexus_table_density = fields.Selection(
        related='nexus_theme_config_id.table_density',
        readonly=False,
        string="Default Data Density"
    )

    nexus_color_preset = fields.Selection(
        related='nexus_theme_config_id.color_preset',
        readonly=False,
        string="Corporate Color Palette"
    )

    nexus_primary_color = fields.Char(
        related='nexus_theme_config_id.primary_color',
        readonly=False,
        string="Primary Brand Color"
    )

    nexus_accent_color = fields.Char(
        related='nexus_theme_config_id.accent_color',
        readonly=False,
        string="Accent Color"
    )

    nexus_sticky_header = fields.Boolean(
        related='nexus_theme_config_id.sticky_header',
        readonly=False,
        string="Sticky Table Headers"
    )

    def _compute_nexus_theme_config(self):
        for record in self:
            config = self.env['nexus.theme.config'].search([
                ('company_id', '=', self.env.company.id),
                ('is_active', '=', True)
            ], limit=1)
            record.nexus_theme_config_id = config.id if config else False

    def _inverse_nexus_theme_config(self):
        for record in self:
            if record.nexus_theme_config_id:
                record.nexus_theme_config_id.is_active = True
