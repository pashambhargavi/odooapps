# -*- coding: utf-8 -*-
from odoo import models, fields, api
from .omni_theme_config import THEME_PRESETS


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    omni_theme_config_id = fields.Many2one(
        'omni.theme.config',
        string='Active OmniTheme Profile',
        help='The company profile governing fallback and corporate styling.'
    )
    omni_default_theme_key = fields.Selection(
        selection=THEME_PRESETS,
        string='Company Default Theme',
        default='emerald_aurora',
        help='Default theme applied to all new users and uncustomized sessions.'
    )
    omni_allow_user_switching = fields.Boolean(
        string='Enable User Systray Switcher',
        default=True,
        help='When enabled, all users see the 10-theme toggle in their navbar.'
    )
    omni_button_border_radius = fields.Selection([
        ('rounded_8', 'Modern Rounded (8px)'),
        ('pill_20', 'Curved Pill (20px)'),
        ('sharp_4', 'Sharp Precision (4px)')
    ], string='Global Button Geometry', default='rounded_8')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        company = self.env.company
        config = self.env['omni.theme.config'].search([
            ('company_id', '=', company.id),
            ('is_active', '=', True)
        ], limit=1)
        if config:
            res.update(
                omni_theme_config_id=config.id,
                omni_default_theme_key=config.theme_key,
                omni_allow_user_switching=config.allow_user_switching,
                omni_button_border_radius=config.button_border_radius,
            )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        company = self.env.company
        config = self.env['omni.theme.config'].search([
            ('company_id', '=', company.id),
            ('is_active', '=', True)
        ], limit=1)
        vals = {
            'theme_key': self.omni_default_theme_key,
            'allow_user_switching': self.omni_allow_user_switching,
            'button_border_radius': self.omni_button_border_radius,
        }
        if config:
            config.write(vals)
            config._onchange_theme_key()
        else:
            vals.update({
                'name': f'Default Studio - {company.name}',
                'company_id': company.id,
                'is_active': True,
            })
            new_config = self.env['omni.theme.config'].create(vals)
            new_config._onchange_theme_key()
