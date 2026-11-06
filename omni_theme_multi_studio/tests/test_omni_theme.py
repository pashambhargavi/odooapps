# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.addons.omni_theme_multi_studio.models.omni_theme_config import THEME_PRESETS, PALETTE_DEFAULTS


class TestOmniTheme(TransactionCase):

    def setUp(self):
        super(TestOmniTheme, self).setUp()
        self.company = self.env.company
        self.user = self.env.user
        self.ConfigModel = self.env['omni.theme.config']

        # Ensure a clean active config
        self.config = self.ConfigModel.search([
            ('company_id', '=', self.company.id),
            ('is_active', '=', True)
        ], limit=1)
        if not self.config:
            self.config = self.ConfigModel.create({
                'name': 'Test Omni Master Studio',
                'company_id': self.company.id,
                'is_active': True,
                'theme_key': 'emerald_aurora',
                'allow_user_switching': True,
                'button_border_radius': 'rounded_8',
            })

    def test_01_default_company_config(self):
        """Test default company configuration is loaded and valid."""
        self.assertTrue(self.config.exists(), "Active OmniTheme configuration should exist.")
        self.assertTrue(self.config.is_active, "Configuration must be active.")
        self.assertEqual(self.config.company_id, self.company, "Config must belong to active test company.")
        self.assertIn(self.config.theme_key, dict(THEME_PRESETS), "Theme key must be a valid preset.")

    def test_02_all_ten_themes_metadata(self):
        """Test get_ten_themes_meta() returns all 10 themes with expected attributes."""
        themes = self.ConfigModel.get_ten_themes_meta()
        self.assertEqual(len(themes), 10, "Must return exactly 10 themes metadata.")

        keys = [t['key'] for t in themes]
        expected_keys = [
            'emerald_aurora', 'cyberpunk_neon', 'royal_velvet', 'sunset_horizon',
            'pristine_paper', 'obsidian_luxe', 'deep_oceanic', 'crimson_apex',
            'forest_zen', 'modern_slate'
        ]
        for ek in expected_keys:
            self.assertIn(ek, keys, f"Theme key {ek} must be present in metadata.")

        # Check that each theme has valid navbar and primary colors
        for t in themes:
            self.assertTrue(t['navbar_bg'].startswith('#'), f"Navbar bg for {t['key']} must be HEX.")
            self.assertTrue(t['primary_color'].startswith('#'), f"Primary color for {t['key']} must be HEX.")
            self.assertTrue(len(t['icon']) > 0, f"Icon for {t['key']} must not be empty.")

    def test_03_user_active_theme_config(self):
        """Test get_user_active_theme_config() returns valid runtime payload."""
        cfg = self.ConfigModel.get_user_active_theme_config()
        self.assertIsInstance(cfg, dict, "Runtime config payload must be a dictionary.")
        self.assertIn('theme_key', cfg)
        self.assertIn('navbar_bg', cfg)
        self.assertIn('primary_color', cfg)
        self.assertIn('button_radius', cfg)
        self.assertEqual(cfg['button_radius'], '8px')
        self.assertEqual(len(cfg['all_themes']), 10)

    def test_04_user_theme_switching(self):
        """Test user theme switching via action_switch_omni_theme."""
        # Switch to Cyberpunk Neon
        res = self.user.action_switch_omni_theme('cyberpunk_neon')
        self.assertTrue(res['success'], "Theme switch should return success True.")
        self.assertEqual(self.user.omni_theme_selection, 'cyberpunk_neon')

        # Test invalid theme key rejection
        res_invalid = self.user.action_switch_omni_theme('non_existent_theme')
        self.assertFalse(res_invalid['success'], "Invalid theme switch must be rejected.")

        # Test cycle theme
        self.user.action_cycle_omni_theme()
        self.assertNotEqual(self.user.omni_theme_selection, 'cyberpunk_neon', "Cycle should advance theme.")

    def test_05_company_preset_apply(self):
        """Test admin action_apply_theme updates and deactivates siblings."""
        new_config = self.ConfigModel.create({
            'name': 'Secondary Obsidian Config',
            'company_id': self.company.id,
            'is_active': False,
            'theme_key': 'obsidian_luxe',
        })
        new_config.action_apply_theme()
        self.assertTrue(new_config.is_active, "New config should become active.")
        self.config.invalidate_recordset()
        self.assertFalse(self.config.is_active, "Previous config should be deactivated.")
        self.assertEqual(new_config.navbar_bg, PALETTE_DEFAULTS['obsidian_luxe']['navbar_bg'])
