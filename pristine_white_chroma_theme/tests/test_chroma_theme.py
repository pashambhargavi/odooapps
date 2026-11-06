# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestChromaTheme(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ChromaConfig = cls.env['chroma.theme.config']
        cls.company = cls.env.company

    def test_01_default_chroma_config_exists(self):
        """Verify default active Pristine Chroma configuration is loaded."""
        config = self.ChromaConfig.search([
            ('company_id', '=', self.company.id),
            ('is_active', '=', True)
        ], limit=1)
        self.assertTrue(config, "Default active Pristine Chroma configuration must exist.")
        self.assertEqual(config.canvas_style, 'pure_white')
        self.assertEqual(config.chroma_preset, 'royal_indigo')
        self.assertEqual(config.header_bg, '#4F46E5')

    def test_02_chroma_preset_switching(self):
        """Verify preset switching auto-updates header and accent colors."""
        config = self.ChromaConfig.create({
            'name': 'Test Sunset Coral Suite',
            'company_id': self.company.id,
            'is_active': False,
            'chroma_preset': 'sunset_coral',
            'canvas_style': 'pure_white',
        })
        config.action_apply_preset()
        self.assertEqual(config.header_bg, '#EA580C')
        self.assertEqual(config.accent_color, '#F97316')

    def test_03_get_active_chroma_config_api(self):
        """Verify get_active_chroma_config() returns a complete configuration dictionary."""
        config_data = self.ChromaConfig.get_active_chroma_config()
        self.assertIsInstance(config_data, dict)
        self.assertIn('canvas_style', config_data)
        self.assertIn('header_bg', config_data)
        self.assertIn('accent_color', config_data)
        self.assertIn('button_shape', config_data)

    def test_04_user_chroma_cycle(self):
        """Verify user 1-click cycle for chromatic header and button colors."""
        user = self.env.user
        initial = user.chroma_personal_preset
        res = user.cycle_chroma_preset()
        self.assertIn('new_preset', res)
        self.assertIn('header_bg', res)
        self.assertNotEqual(user.chroma_personal_preset, initial)

    def test_05_res_config_settings_integration(self):
        """Verify res.config.settings integration reads and writes active config."""
        settings = self.env['res.config.settings'].create({})
        self.assertTrue(settings.chroma_theme_config_id, "Settings must locate active Chroma config.")
        self.assertEqual(settings.chroma_canvas_style, settings.chroma_theme_config_id.canvas_style)
        self.assertEqual(settings.chroma_preset, settings.chroma_theme_config_id.chroma_preset)
