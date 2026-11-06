# -*- coding: utf-8 -*-
{
    'name': 'Minimal Luxe Backend Theme | Linear Monochrome & Zen Focus Studio',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Linear Monochrome Canvas, Hairline 1px Precision Borders, 1-Click Zen Focus Mode, 5 Luxury Metal Accents & Tabular Ledger Typography for Community & Enterprise',
    'description': """
Minimal Luxe Backend Theme & Zen Focus Studio
=============================================
Distraction-free executive interface inspired by Linear.app, Stripe, Apple, and Notion.

Key Innovations:
----------------
* **Ultra-Clean Monochromatic Architecture**: Obsidian Black (#09090B), Crisp Chalk White (#FAFAFA), and Studio Zinc (#18181B).
* **1-Click Zen Focus Mode**: Live systray toggle that dims chrome and background noise to put 100% focus on the active document.
* **5 Luxury Metal Accents**: 24K Sovereign Gold, Pure Titanium, Platinum Ice, Emerald Mint, and Rose Gold.
* **Hairline 1px Precision Borders**: Crisp razor-thin borders for cards, modals, and input fields.
* **Tabular Financial Typography**: JetBrains Mono numbers for currency cells, quantities, and ledger balances.
* **Executive Branded Split-Screen Login**: High-fashion split-screen login layout with brand statistics and secure credentials card.
* **100% Native Architecture**: Zero third-party dependencies, zero CDN reliance, universal compatibility across Odoo v14 through v20.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'support': 'bhargavipasham2000@gmail.com',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/minimal_luxe_security.xml',
        'security/ir.model.access.csv',
        'data/minimal_luxe_default_data.xml',
        'views/minimal_luxe_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'minimal_luxe_backend_theme/static/src/scss/variables.scss',
            'minimal_luxe_backend_theme/static/src/scss/minimal_surface.scss',
            'minimal_luxe_backend_theme/static/src/scss/zen_mode.scss',
            'minimal_luxe_backend_theme/static/src/scss/mono_tables.scss',
            'minimal_luxe_backend_theme/static/src/scss/mobile_minimal.scss',
            'minimal_luxe_backend_theme/static/src/js/minimal_luxe_service.js',
            'minimal_luxe_backend_theme/static/src/js/zen_toggle.js',
            'minimal_luxe_backend_theme/static/src/js/accent_toggle.js',
            'minimal_luxe_backend_theme/static/src/xml/luxe_systray.xml',
        ],
        'web.assets_frontend': [
            'minimal_luxe_backend_theme/static/src/scss/variables.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
