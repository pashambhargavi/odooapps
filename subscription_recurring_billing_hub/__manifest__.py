# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Subscription, Recurring Billing & Contract Management Hub',
    'version': '15.0.1.0.0',
    'category': 'Sales/Subscriptions',
    'summary': 'Automated Recurring Billing, Subscription Lifecycle, Contract Renewal Engine, MRR/ARR Metrics & 1-Click Invoice Generation',
    'description': """
Subscription, Recurring Billing & Contract Management Hub for Odoo 18 Community
================================================================================
Turn your Odoo Community into a high-powered Subscription & Recurring Revenue Engine!
Standard Odoo Community lacks any subscription management tool. This all-in-one module
enables SaaS providers, maintenance contractors, service agencies, gyms, and subscription
businesses to manage contracts, automate recurring billing, track MRR/ARR, and eliminate churn.

Key Features & Business Benefits
---------------------------------
* **Flexible Recurring Billing Plans:**
  - Support Daily, Weekly, Monthly, Quarterly, Semi-Annual, and Yearly billing cycles.
  - Configurable auto-invoicing, auto-posting, and advance renewal reminders.
* **Complete Contract Lifecycle Management:**
  - Track stages: Draft -> Active (In Progress) -> Paused -> Expired -> Closed / Cancelled.
  - Start dates, end dates, trial periods, and automated next invoice scheduling.
* **Automated Recurring Invoicing & Scheduler:**
  - Automated cron scheduler creates recurring customer invoices (`account.move`) on due dates.
  - Manual on-demand 1-click invoice generation with smart links.
* **MRR & ARR Analytics Dashboard:**
  - Real-time computation of Monthly Recurring Revenue (MRR) and Annual Recurring Revenue (ARR).
  - Visual Kanban badges, pivot reports, and contract financial metrics.
* **1-Click Renewal & Upsell Wizard:**
  - Fast contract renewal wizard to extend terms, adjust pricing, or renew expired accounts.
* **Native Sales & Invoice Integration:**
  - Convert any confirmed Sales Order into an active Subscription Contract with 1 click.
  - Linked invoice history on contracts and customer partner cards.
* **Professional PDF Contract Agreement:**
  - Print customer-ready Subscription Service Agreements with legal terms & signatures.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 89.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/subscription_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/subscription_plan_data.xml',
        'wizard/subscription_renew_wizard_views.xml',
        'views/subscription_plan_views.xml',
        'views/subscription_contract_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/subscription_menus.xml',
        'report/subscription_report.xml',
        'report/subscription_report_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}



