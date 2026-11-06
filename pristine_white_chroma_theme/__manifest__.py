# -*- coding: utf-8 -*-
{
    'name': 'Pristine White Chroma Theme | Crisp White Canvas & Vibrant Header Studio',
    'version': '19.0.1.0.0',
    'category': 'Themes/Backend',
    'summary': '100% Pure Crisp White Views, Paper-Like Form Elevation, Vibrant Chromatic Headers & Glowing Action Buttons for Community & Enterprise',
    'description': """
Pristine White Chroma Theme & Vibrant Action Studio
===================================================
Engineered for high-output daylight enterprise operations with 100% pure white views and vibrant chromatic controls.

Key Innovations:
----------------
* **100% Pure White Paper Canvas**: Zero grey mud. Every form sheet, kanban stage, list table, and modal renders on crisp, immaculate clean white (#FFFFFF).
* **Vibrant Chromatic Header Engine**: Electric Royal Indigo (#4F46E5), Vibrant Sunset Coral (#EA580C), Emerald Mint (#059669), Hyper Violet (#7C3AED), Ocean Cyan (#0284C7), and Ruby Rose (#E11D48).
* **1-Click Systray Header Color Switcher**: Cycle through vibrant corporate palettes instantly from the top navbar.
* **Vibrant Primary Action Buttons**: High-energy action buttons (Create, Save, Confirm, Send) with soft glow aura, paired with crisp white secondary buttons.
* **Paper-Like Form Elevation**: Gentle floating card shadows (0 4px 16px rgba(0,0,0,0.04)) with crisp 1px hairline dividers.
* **Pristine White Split-Screen Login**: High-converting enterprise portal with vibrant chromatic hero banner and clean white credentials card.
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
        'security/chroma_security.xml',
        'security/ir.model.access.csv',
        'data/chroma_default_data.xml',
        'views/chroma_theme_config_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/login_templates.xml',
        'views/theme_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'pristine_white_chroma_theme/static/src/scss/variables.scss',
            'pristine_white_chroma_theme/static/src/scss/pristine_canvas.scss',
            'pristine_white_chroma_theme/static/src/scss/vibrant_headers.scss',
            'pristine_white_chroma_theme/static/src/scss/button_accents.scss',
            'pristine_white_chroma_theme/static/src/scss/mobile_chroma.scss',
            'pristine_white_chroma_theme/static/src/js/chroma_theme_service.js',
            'pristine_white_chroma_theme/static/src/js/chroma_toggle.js',
            'pristine_white_chroma_theme/static/src/xml/chroma_systray.xml',
        ],
        'web.assets_frontend': [
            'pristine_white_chroma_theme/static/src/scss/variables.scss',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
