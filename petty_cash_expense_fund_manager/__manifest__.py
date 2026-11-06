# -*- coding: utf-8 -*-
{
    'name': 'Petty Cash, Multi-Custodian Imprest Fund & Expense Manager',
    'version': '14.0.1.0.0',
    'category': 'Accounting/Invoicing',
    'summary': 'Multi-Custodian Petty Cash Boxes, Imprest Float Cycles, Denomination Tally Sheets, Expense Vouchers & Bank Replenishments for Odoo Community',
    'sequence': 12,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'license': 'LGPL-3',
    # 'price': 119.00,
    # 'currency': 'EUR',
    'depends': [
        'base',
        'account',
        'mail',
    ],
    'data': [
        'security/petty_cash_security.xml',
        'security/ir.model.access.csv',
        'data/petty_cash_sequence_data.xml',
        'report/petty_cash_report.xml',
        'views/petty_cash_voucher_views.xml',
        'views/petty_cash_replenishment_views.xml',
        'views/petty_cash_fund_views.xml',
        'views/wizard_denomination_tally_views.xml',
        'views/petty_cash_menus.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}




