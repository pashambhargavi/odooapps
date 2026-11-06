# -*- coding: utf-8 -*-
{
    'name': 'Nexus Pro Backend Theme | 3-in-1 Layouts, Split Chatter & Density Studio',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': 'Adaptive 3-in-1 Navigation (Sidebar/Topbar/Mini-Rail), 1-Click Side-by-Side Chatter, Compact Table Density & 6 Corporate Palettes for Community & Enterprise',
    'description': """
Nexus Pro Backend Theme & Productivity Studio
=============================================
Universal high-performance enterprise interface inspired by the best productivity suites (Spiffy & Arc).

Key Innovations:
----------------
* **3-in-1 Adaptive Layouts**: Seamlessly switch between SaaS Left Sidebar, Enterprise Topbar, and Slim 60px Mini-Rail.
* **1-Click Smart Chatter Placement**: Live toggle chatter position between Side-by-Side (Right Column Split) and Bottom Stacked directly from the systray.
* **3 Data Density Modes**: Compact Density for financial accounting ledgers, Standard ERP, and Spacious Touch for tablets.
* **Sticky Table Headers & Totals**: Column headers and ledger total rows stay pinned during deep scrolls.
* **6 Curated Corporate Color Engines**: Royal Sapphire, FinTech Emerald, Imperial Amethyst, OLED Dark, Crimson Titan, and Nordic Slate.
* **Mobile Floating Action Dock**: Handheld navigation bar pinned to the bottom of iOS and Android viewports.
* **Executive Branded Split-Screen Login**: High-converting corporate authentication portal with stat callouts and security badges.
* **100% Native Architecture**: Zero third-party dependencies, zero CDN reliance, universal Odoo v14 through v20 support.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'support': 'bhargavipasham2000@gmail.com',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'security/nexus_security.xml',
        'security/ir.model.access.csv',
        'data/nexus_default_data.xml',
        'views/nexus_theme_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'nexus_backend_theme_pro/static/src/scss/variables.scss',
            'nexus_backend_theme_pro/static/src/scss/sidebar_layout.scss',
            'nexus_backend_theme_pro/static/src/scss/topbar_layout.scss',
            'nexus_backend_theme_pro/static/src/scss/chatter_split.scss',
            'nexus_backend_theme_pro/static/src/scss/density_modes.scss',
            'nexus_backend_theme_pro/static/src/scss/mobile_dock.scss',
            'nexus_backend_theme_pro/static/src/js/nexus_theme_service.js',
            'nexus_backend_theme_pro/static/src/js/chatter_toggle.js',
            'nexus_backend_theme_pro/static/src/js/layout_toggle.js',
            'nexus_backend_theme_pro/static/src/xml/nexus_systray.xml',
        ],
        'web.assets_frontend': [
            'nexus_backend_theme_pro/static/src/scss/variables.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
