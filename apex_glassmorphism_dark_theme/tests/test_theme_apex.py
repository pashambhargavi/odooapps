# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestThemeApex(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ApexConfig = cls.env['theme.apex.config']
        cls.company = cls.env.company

        cls.config = cls.ApexConfig.search([('company_id', '=', cls.company.id), ('is_active', '=', True)], limit=1)
        if not cls.config:
            cls.config = cls.ApexConfig.create({
                'name': 'Test Apex Profile',
                'company_id': cls.company.id,
                'is_active': True,
                'neon_preset': 'electric_cyan',
                'neon_color': '#00F0FF',
            })

    def test_01_default_apex_config_exists(self):
        """Test default active Apex Cyber profile exists."""
        self.assertTrue(self.config.exists())
        self.assertEqual(self.config.is_active, True)
        self.assertEqual(self.config.neon_color, '#00F0FF')

    def test_02_neon_preset_switching(self):
        """Test switching neon presets updates colors and glow parameters."""
        cfg = self.ApexConfig.create({
            'name': 'Magenta Test',
            'company_id': self.company.id,
            'neon_preset': 'cyber_magenta',
        })
        cfg._onchange_neon_preset()
        self.assertEqual(cfg.neon_color, '#FF007F', "Should update to Cyberpunk Magenta.")

        cfg.neon_preset = 'neon_emerald'
        cfg._onchange_neon_preset()
        self.assertEqual(cfg.neon_color, '#10B981', "Should update to Matrix Neon Emerald.")

    def test_03_get_active_apex_config(self):
        """Test get_active_apex_config API method returns valid styling dictionary."""
        data = self.ApexConfig.get_active_apex_config()
        self.assertIsInstance(data, dict)
        self.assertIn('neon_color', data)
        self.assertIn('glass_blur_strength', data)
        self.assertIn('enable_glass_app_drawer', data)

    def test_04_user_cycle_neon_mood(self):
        """Test user cycling through personal neon moods."""
        user = self.env.user
        user.apex_neon_preset = 'electric_cyan'
        res = user.cycle_neon_mood()
        self.assertEqual(res['new_mood'], 'cyber_magenta')
        self.assertEqual(user.apex_neon_preset, 'cyber_magenta')

    def test_05_res_config_settings_apex_integration(self):
        """Test configuring Apex theme via res.config.settings wizard."""
        Settings = self.env['res.config.settings']
        settings = Settings.create({})
        self.assertTrue(settings.apex_theme_config_id)
        settings.apex_neon_preset = 'ultraviolet'
        self.assertEqual(self.config.neon_preset, 'ultraviolet')
