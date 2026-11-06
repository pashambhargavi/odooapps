# -*- coding: utf-8 -*-
{
    'name': 'OmniTheme 10-in-1 Backend Theme Studio | Instant 1-Click Multi-Theme Engine',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': '10 distinct enterprise backend themes in one single app. 1-click systray toggle, zero page reload, pure white paper views, dark neon OLED, and luxury presets.',
    'description': """
OmniTheme 10-in-1 Backend Theme Studio
======================================
The ultimate multi-theme powerhouse for Odoo Community and Enterprise. Switch effortlessly between 10 professionally designed themes with a single click in your top navigation bar.

Included 10-Theme Roster:
-------------------------
1. Emerald Aurora (Nordic Emerald Teal & Fresh Mint)
2. Cyberpunk Neon (Midnight Dark Mode & Electric Cyan / Magenta)
3. Royal Velvet (Imperial Deep Amethyst & Sovereign Gold)
4. Sunset Horizon (Warm Terracotta & Solar Amber Coral)
5. Pristine Paper (100% Pure Crisp White Views & Cobalt Blue)
6. Obsidian Luxe (Linear Jet Black & Hairline Platinum Accents)
7. Deep Oceanic (Bermuda Maritime Navy & Seafoam Turquoise)
8. Crimson Apex (Executive Burgundy & Commanding Scarlet)
9. Forest Zen (Organic Bamboo Sage & Calming Matcha Moss)
10. Modern Slate (Silicon Valley Tech Slate & Electric Indigo)

Key Capabilities:
-----------------
* 1-Click Systray Multi-Theme Switcher (Zero page reload)
* Individual User Preferences & Company Master Branding
* Modern Rounded (8px), Curved Pill (20px), or Sharp (4px) Button Geometries
* Multi-Company Theme Enforcement & Access Permissions
* Executive Split-Screen Branded Login Portal
* Mobile & Tablet Responsive Floating Dock
* 100% Native Architecture, Zero Third-Party Dependencies
    """,
    'author': 'Bhargavi Pasham',
    'support': 'bhargavipasham2000@gmail.com',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'license': 'OPL-1',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'security/omni_security.xml',
        'security/ir.model.access.csv',
        'data/omni_default_data.xml',
        'views/omni_theme_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            'omni_theme_multi_studio/static/src/scss/omni_variables.scss',
        ],
        'web.assets_backend': [
            'omni_theme_multi_studio/static/src/scss/omni_themes.scss',
            'omni_theme_multi_studio/static/src/scss/omni_components.scss',
            'omni_theme_multi_studio/static/src/scss/omni_mobile.scss',
            'omni_theme_multi_studio/static/src/xml/omni_systray.xml',
            'omni_theme_multi_studio/static/src/js/omni_theme_service.js',
            'omni_theme_multi_studio/static/src/js/omni_systray_toggle.js',
        ],
    },
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
