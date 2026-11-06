# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestNexusTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ThemeConfig = cls.env['nexus.theme.config']
        cls.company = cls.env.company

    def test_01_default_nexus_config_exists(self):
        """Verify default active Nexus Pro configuration is loaded."""
        config = self.ThemeConfig.search([
            ('company_id', '=', self.company.id),
            ('is_active', '=', True)
        ], limit=1)
        self.assertTrue(config, "Default active Nexus theme configuration must exist.")
        self.assertEqual(config.layout_mode, 'sidebar')
        self.assertEqual(config.chatter_position, 'sided')
        self.assertEqual(config.table_density, 'standard')
        self.assertEqual(config.color_preset, 'sapphire')

    def test_02_preset_switching_and_colors(self):
        """Verify preset switching auto-updates primary and accent colors."""
        config = self.ThemeConfig.create({
            'name': 'Test FinTech Suite',
            'company_id': self.company.id,
            'is_active': False,
            'color_preset': 'emerald',
            'layout_mode': 'topbar',
            'chatter_position': 'bottom',
            'table_density': 'compact',
        })
        config.action_apply_preset()
        self.assertEqual(config.primary_color, '#065F46')
        self.assertEqual(config.accent_color, '#10B981')
        self.assertEqual(config.sidebar_bg, '#064E3B')

    def test_03_get_active_nexus_config_api(self):
        """Verify get_active_nexus_config() returns a complete dictionary."""
        config_data = self.ThemeConfig.get_active_nexus_config()
        self.assertIsInstance(config_data, dict)
        self.assertIn('layout_mode', config_data)
        self.assertIn('chatter_position', config_data)
        self.assertIn('table_density', config_data)
        self.assertIn('primary_color', config_data)
        self.assertIn('accent_color', config_data)

    def test_04_user_chatter_and_layout_toggles(self):
        """Verify user 1-click toggles for chatter and layout."""
        user = self.env.user
        # Toggle chatter
        initial_chatter = user.nexus_chatter_position
        res_chatter = user.toggle_chatter_position()
        self.assertIn('new_position', res_chatter)
        self.assertNotEqual(user.nexus_chatter_position, initial_chatter)

        # Cycle layout
        res_layout = user.cycle_layout_mode()
        self.assertIn('new_layout', res_layout)
        self.assertIn(res_layout['new_layout'], ['sidebar', 'topbar', 'minirail'])

        # Toggle density
        res_density = user.toggle_table_density()
        self.assertIn('new_density', res_density)
        self.assertIn(res_density['new_density'], ['compact', 'standard', 'spacious'])

    def test_05_res_config_settings_integration(self):
        """Verify res.config.settings integration reads and writes active config."""
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.nexus_theme_config_id, "Settings must locate active Nexus config.")
        self.assertEqual(settings.nexus_layout_mode, settings.nexus_theme_config_id.layout_mode)
        self.assertEqual(settings.nexus_chatter_position, settings.nexus_theme_config_id.chatter_position)
