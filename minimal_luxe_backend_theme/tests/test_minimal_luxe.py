# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestMinimalLuxeTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.LuxeConfig = cls.env['minimal.luxe.config']
        cls.company = cls.env.company

    def test_01_default_luxe_config_exists(self):
        """Verify default active Minimal Luxe configuration is loaded."""
        config = self.LuxeConfig.search([
            ('company_id', '=', self.company.id),
            ('is_active', '=', True)
        ], limit=1)
        self.assertTrue(config, "Default active Minimal Luxe configuration must exist.")
        self.assertEqual(config.theme_mode, 'obsidian_dark')
        self.assertEqual(config.luxury_accent, 'sovereign_gold')
        self.assertTrue(config.zen_mode_enabled)

    def test_02_luxury_accent_switching(self):
        """Verify luxury accent switching updates accent HEX."""
        config = self.LuxeConfig.create({
            'name': 'Test Platinum Ice Suite',
            'company_id': self.company.id,
            'is_active': False,
            'luxury_accent': 'platinum_ice',
            'theme_mode': 'chalk_light',
        })
        config.action_apply_accent()
        self.assertEqual(config.accent_hex, '#38BDF8')

    def test_03_get_active_luxe_config_api(self):
        """Verify get_active_luxe_config() returns valid configuration dictionary."""
        config_data = self.LuxeConfig.get_active_luxe_config()
        self.assertIsInstance(config_data, dict)
        self.assertIn('theme_mode', config_data)
        self.assertIn('luxury_accent', config_data)
        self.assertIn('accent_hex', config_data)
        self.assertIn('zen_mode_enabled', config_data)

    def test_04_user_zen_mode_toggle(self):
        """Verify user 1-click toggle for Zen focus mode and luxury accent."""
        user = self.env.user
        initial_zen = user.luxe_zen_mode
        res_zen = user.toggle_zen_mode()
        self.assertIn('zen_mode_active', res_zen)
        self.assertNotEqual(user.luxe_zen_mode, initial_zen)

        # Cycle luxury accent
        res_accent = user.cycle_luxury_accent()
        self.assertIn('new_accent', res_accent)
        self.assertIn('accent_hex', res_accent)

    def test_05_res_config_settings_integration(self):
        """Verify res.config.settings integration reads and writes active config."""
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.luxe_theme_config_id, "Settings must locate active Luxe config.")
        self.assertEqual(settings.luxe_theme_mode, settings.luxe_theme_config_id.theme_mode)
        self.assertEqual(settings.luxe_luxury_accent, settings.luxe_theme_config_id.luxury_accent)
