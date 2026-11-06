# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Fixed Asset Management & Depreciation Hub',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Fixed asset register, linear & declining-balance depreciation boards, automatic monthly posting, '
               'vendor-bill asset capture and disposal entries for Odoo Community',
    'description': """
Fixed Asset Management & Depreciation Hub for Odoo 18 Community
==============================================================
Asset accounting is an Enterprise-only feature in standard Odoo. This module brings a complete,
auditable fixed asset register to Odoo Community:

* Asset categories with asset, accumulated depreciation, expense and disposal-loss accounts.
* Linear and declining-balance (with automatic switch to linear) depreciation methods.
* Monthly or yearly periods, optional daily prorata for the first period, salvage value.
* One-click depreciation board computation.
* Automatic posting of due depreciation entries through a daily scheduled action.
* Draft assets created automatically when a vendor bill line carries an asset category.
* Disposal / scrap wizard that removes the asset and books the remaining net book value as a loss.
* Printable depreciation schedule (PDF), pivot and graph analysis of depreciation lines.
* Multi-company record rules.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 99.00,
    # 'currency': 'USD',
    'depends': ['account'],
    'data': [
        'security/asset_security.xml',
        'security/ir.model.access.csv',
        'data/asset_cron.xml',
        'wizard/asset_dispose_wizard_views.xml',
        'views/asset_category_views.xml',
        'views/asset_views.xml',
        'views/asset_line_views.xml',
        'views/account_move_views.xml',
        'views/asset_menus.xml',
        'report/asset_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}

