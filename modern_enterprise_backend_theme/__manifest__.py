# -*- coding: utf-8 -*-
{
    'name': 'NextGen Enterprise Backend Theme & Modern UI Hub',
    'version': '16.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Enterprise App Switcher, Dark Mode, Collapsible Left Sidebar, Brand Color Customizer, Sticky Headers & Mobile UX for Community & Enterprise',
    'description': """
NextGen Enterprise Pro Backend Theme & Modern UI Hub
====================================================
Transforms Odoo Community and Enterprise with a sleek, high-performance executive design system.

Key Capabilities:
-----------------
* **Enterprise Fullscreen App Switcher**: Signature high-speed app drawer grid with real-time fuzzy search.
* **Modern Left Collapsible Sidebar**: Optional SaaS-style collapsible vertical navigation rail with icon tooltips.
* **True Dark Mode Suite**: 1-click systray toggle with high-contrast night palette for forms, lists, kanbans, and chatters.
* **No-Code Brand Color Customizer**: 6 executive color presets (Enterprise Violet, Deep Navy, Emerald Tech, Sapphire Blue, Crimson Luxury, Dark Slate) plus custom HEX color pickers.
* **Sticky Table Headers & Form Statusbar**: Eliminates scrolling fatigue on dense data tables and form views.
* **Mobile Touch Navigation**: Smartphone bottom navigation bar and touch drawers for iOS and Android.
* **Executive Split-Screen Login Page**: Replaces default login with a branded enterprise portal.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'support': 'bhargavipasham2000@gmail.com',
    # 'price': 149.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/theme_security.xml',
        'security/ir.model.access.csv',
        'data/theme_default_data.xml',
        'views/theme_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'modern_enterprise_backend_theme/static/src/scss/variables.scss',
            'modern_enterprise_backend_theme/static/src/scss/app_switcher.scss',
            'modern_enterprise_backend_theme/static/src/scss/sidebar.scss',
            'modern_enterprise_backend_theme/static/src/scss/dark_mode.scss',
            'modern_enterprise_backend_theme/static/src/scss/sticky_headers.scss',
            'modern_enterprise_backend_theme/static/src/scss/mobile.scss',
            'modern_enterprise_backend_theme/static/src/js/dark_mode_toggle.js',
            'modern_enterprise_backend_theme/static/src/js/theme_service.js',
            'modern_enterprise_backend_theme/static/src/xml/dark_mode_toggle.xml',
        ],
        'web.assets_frontend': [
            'modern_enterprise_backend_theme/static/src/scss/variables.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}


