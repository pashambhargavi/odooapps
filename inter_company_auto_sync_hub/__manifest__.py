# -*- coding: utf-8 -*-
{
    'name': 'Inter-Company Automated Transactions & Mirroring Hub | SO, PO, Invoice & Stock Delivery Sync',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Sales/Purchase',
    'summary': 'Automate reciprocal Purchase Orders, Sales Orders, Customer Invoices, Vendor Bills, and Stock Pickings across subsidiary entities with dynamic transfer pricing margin rules.',
    'description': """
Inter-Company Automated Transactions & Mirroring Hub
=====================================================
Eliminate double data entry, billing discrepancies, and inter-company reconciliation friction across your group entities.

Key Innovations:
----------------
* Bidirectional Document Mirroring (PO -> SO, SO -> PO, Invoice -> Bill, Delivery -> Receipt).
* Smart Transfer Pricing Rules (Cost-plus margin %, Discount from list, or Custom pricelists).
* Automated Inter-Company Clearing & Elimination tagging.
* Reciprocal Smart Buttons on Orders, Invoices, and Pickings for instant 1-click cross-company navigation.
* Multi-Company Security Isolation & Complete Audit Execution Logs.
* Executive QWeb PDF Inter-Company Audit Statement.
    """,
    'author': 'Bhargavi Pasham',
    'support': 'bhargavipasham2000@gmail.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale_management',
        'purchase',
        'account',
        'stock',
    ],
    'data': [
        'security/inter_company_security.xml',
        'security/ir.model.access.csv',
        'data/inter_company_data.xml',
        'views/inter_company_rule_views.xml',
        'views/purchase_order_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'report/inter_company_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    # 'price': 249.00,
    # 'currency': 'EUR',
}
