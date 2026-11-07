# -*- coding: utf-8 -*-
{
    'name': 'Advanced Subscriptions & Recurring Billing Engine Pro | Automated Invoicing, Prorata Upgrades, Churn & MRR Analytics',
    'version': '18.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Standalone Enterprise Recurring Billing, SaaS Subscription Contracts, Auto Invoicing, Prorata Upgrades/Downgrades, Dunning Automation, Churn & MRR/ARR Dashboard (Community & Enterprise)',
    'description': """
Advanced Subscriptions & Recurring Billing Engine Pro
=====================================================
A full-featured recurring revenue, contract management, and subscription invoicing engine engineered for both Odoo Community and Enterprise.

Key Functional Innovations:
---------------------------
* **Independent Recurring Engine:** Run complete subscription contracts on Odoo Community without needing Enterprise `sale_subscription`.
* **Flexible Billing Intervals:** Daily, Weekly, Monthly, Quarterly, Semi-Annual, and Annual billing frequencies with customizable grace periods and trial days.
* **Automated Recurring Invoicing:** Daily scheduler generates and posts customer invoices on the contract schedule date with smart links and automatic date advancement.
* **Prorata Plan Upgrades & Downgrades:** Mid-cycle contract adjustments automatically calculate credit balances and prorated invoice amounts.
* **SaaS Revenue Metrics (MRR & ARR):** Real-time Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR) calculation per subscription, customer, and cohort.
* **Automated Dunning & Churn Prevention:** Automated reminder stages and escalation rules for overdue subscription invoices.
* **Executive Boardroom QWeb PDF Contract:** Official subscription agreement and renewal schedules with legal terms and signature blocks.
* **Multi-Company Security:** Rigid multi-company isolation with immutable chatter audit logs.
    """,
    'author': 'Bhargavi Pasham',
    'support': 'bhargavipasham2000@gmail.com',
    'license': 'LGPL-3',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'depends': ['base', 'account', 'sale_management', 'mail'],
    'data': [
        'security/subscription_security.xml',
        'security/ir.model.access.csv',
        'data/subscription_sequence.xml',
        'data/subscription_cron.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'report/subscription_reports.xml',
        'report/subscription_contract_report.xml',
    ],
    'demo': [],
    'images': [
        'static/description/banner.png',
        'static/description/icon.png',
        'static/description/theme_preview.gif',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
