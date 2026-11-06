# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase, tagged

@tagged('post_install', '-at_install')
class TestThemeConfiguration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ThemeConfig = cls.env['theme.config']
        cls.company = cls.env.company

        # Ensure an active theme config exists
        cls.theme = cls.ThemeConfig.search([('company_id', '=', cls.company.id), ('is_active', '=', True)], limit=1)
        if not cls.theme:
            cls.theme = cls.ThemeConfig.create({
                'name': 'Test Corporate Theme',
                'company_id': cls.company.id,
                'is_active': True,
                'layout_mode': 'enterprise_top',
                'color_preset': 'executive_navy',
                'primary_color': '#0F172A',
                'accent_color': '#2563EB',
                'navbar_bg_color': '#0F172A',
                'sidebar_bg_color': '#1E293B',
                'active_item_color': '#38BDF8',
            })

    def test_01_default_theme_loaded(self):
        """Test active theme exists and has expected default structure."""
        self.assertTrue(self.theme.exists(), "Active theme profile must exist.")
        self.assertEqual(self.theme.is_active, True)
        self.assertEqual(self.theme.layout_mode, 'enterprise_top')

    def test_02_color_preset_onchange(self):
        """Test switching presets dynamically updates brand color fields."""
        theme = self.ThemeConfig.create({
            'name': 'Preset Test Theme',
            'company_id': self.company.id,
            'color_preset': 'enterprise_violet',
        })
        theme._onchange_color_preset()
        self.assertEqual(theme.primary_color, '#714B67', "Primary color should update to Enterprise Violet.")
        self.assertEqual(theme.accent_color, '#00A09D', "Accent color should update.")

        # Test Emerald Tech
        theme.color_preset = 'emerald_tech'
        theme._onchange_color_preset()
        self.assertEqual(theme.primary_color, '#065F46', "Primary color should update to Emerald Tech.")

    def test_03_get_active_theme_config(self):
        """Test API method returning active theme dictionary for the frontend."""
        data = self.ThemeConfig.get_active_theme_config()
        self.assertIsInstance(data, dict)
        self.assertIn('primary_color', data)
        self.assertIn('navbar_bg_color', data)
        self.assertIn('layout_mode', data)
        self.assertIn('font_family', data)

    def test_04_user_dark_mode_toggle(self):
        """Test 1-click user dark mode toggle in res.users."""
        user = self.env.user
        user.theme_dark_mode = 'light'

        # Toggle to dark
        res = user.toggle_dark_mode()
        self.assertEqual(res['new_mode'], 'dark')
        self.assertEqual(user.theme_dark_mode, 'dark')

        # Toggle back to light
        res = user.toggle_dark_mode()
        self.assertEqual(res['new_mode'], 'light')
        self.assertEqual(user.theme_dark_mode, 'light')

    def test_05_res_config_settings_integration(self):
        """Test modifying theme settings via res.config.settings wizard."""
        Settings = self.env['res.config.settings']
        settings = Settings.create({})
        self.assertTrue(settings.theme_config_id)
        self.assertEqual(settings.theme_layout_mode, self.theme.layout_mode)

        # Update via settings
        settings.theme_layout_mode = 'modern_sidebar'
        self.assertEqual(self.theme.layout_mode, 'modern_sidebar')
