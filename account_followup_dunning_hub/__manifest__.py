# -*- coding: utf-8 -*-
{
    'name': 'Customer Payment Follow-Up, Overdue Aging & Automated Dunning Hub',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Invoicing',
    'summary': 'Automated Multi-Stage Payment Reminders, Overdue Aging Analysis, Dunning Escalations & Statement of Account PDFs for Odoo Community',
    'sequence': 10,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'license': 'LGPL-3',
    # 'price': 99.00,
    # 'currency': 'EUR',
    'depends': [
        'base',
        'account',
        'mail',
    ],
    'data': [
        'security/followup_security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'data/followup_level_data.xml',
        'data/followup_cron_data.xml',
        'report/statement_of_account_report.xml',
        'views/account_followup_level_views.xml',
        'views/account_followup_history_views.xml',
        'views/account_move_views.xml',
        'views/wizard_manual_followup_views.xml',
        'views/res_partner_followup_views.xml',
        'views/followup_menus.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

