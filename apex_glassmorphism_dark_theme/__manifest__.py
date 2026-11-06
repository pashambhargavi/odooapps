# -*- coding: utf-8 -*-
{
    'name': 'Apex Glassmorphism & Cyber Neon Dark Theme | Futuristic ERP UI',
    'version': '18.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Frosted Glass Cards, Cyber Neon Ambient Glow, Floating App Switcher, OLED Dark Mode & Mobile Glass Dock for Community & Enterprise',
    'description': """
Apex Glassmorphism & Cyber Neon Dark Theme
==========================================
Ultra-Modern Futuristic Executive Interface for Odoo Community and Enterprise.

Key Innovations:
----------------
* **Frosted Acrylic Glassmorphism**: Translucent floating cards with real-time backdrop blur (8px, 16px, 24px).
* **Cyber Neon Ambient Lighting**: 5 Luminous Neon presets (Electric Cyan, Cyberpunk Magenta, Neon Emerald, Ultraviolet, Solar Gold) + custom color pickers.
* **Translucent App Switcher Drawer**: Frosted glass full-screen launcher with fuzzy search and glowing neon tile hover states.
* **OLED Cyber Dark Palette**: Deep space canvas (#050811) with vibrant glowing data indicators and high legibility.
* **Glowing Input Focus Rings**: Interactive glowing borders on form fields and active status pills.
* **Mobile Floating Glass Dock**: Bottom floating acrylic dock for iOS and Android devices.
* **Futuristic Branded Login Portal**: Split-screen glass authentication portal with cybernetic value messaging.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'support': 'bhargavipasham2000@gmail.com',
    # 'price': 189.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/theme_apex_security.xml',
        'security/ir.model.access.csv',
        'data/theme_apex_default_data.xml',
        'views/theme_apex_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'apex_glassmorphism_dark_theme/static/src/scss/variables.scss',
            'apex_glassmorphism_dark_theme/static/src/scss/glassmorphism.scss',
            'apex_glassmorphism_dark_theme/static/src/scss/neon_accents.scss',
            'apex_glassmorphism_dark_theme/static/src/scss/app_drawer.scss',
            'apex_glassmorphism_dark_theme/static/src/scss/mobile_dock.scss',
            'apex_glassmorphism_dark_theme/static/src/js/neon_toggle.js',
            'apex_glassmorphism_dark_theme/static/src/js/apex_theme_service.js',
            'apex_glassmorphism_dark_theme/static/src/xml/neon_toggle.xml',
        ],
        'web.assets_frontend': [
            'apex_glassmorphism_dark_theme/static/src/scss/variables.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
