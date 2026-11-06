# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Smart Helpdesk, SLA Policy & Customer Support Hub',
    'version': '16.0.1.0.0',
    'category': 'Services/Helpdesk',
    'summary': 'Enterprise-Grade Helpdesk Tickets, Dynamic SLA Policies, Support Teams, Sales/Invoice Integration & Service Reports',
    'description': """
Smart Helpdesk, SLA Policy & Customer Support Hub for Odoo 18 Community
=======================================================================
Bring a complete, modern Customer Support & Helpdesk SLA system to Odoo 18 Community Edition:

Key Features
------------
* **Support Teams & Kanban Dashboard:** Organize support agents into specialized teams (Customer Support, Technical & Warranty, Billing & Finance) with real-time counts of Unassigned, Open, High-Priority, and SLA-Breached tickets.
* **Dynamic SLA Policy Engine:** Define response and resolution time targets (in hours) based on Team, Priority, and Ticket Type, with automatic deadline computation (`Response Deadline` & `Resolution Deadline`) and scheduled breach alerts.
* **End-to-End Ticket Lifecycle:** Track tickets across customizable Kanban stages (New, In Progress, Waiting on Customer, Solved, Canceled) with automatic First Response Time, Total Resolution Hours, and Customer Satisfaction Rating (1–5 Stars).
* **Deep Sales, Invoice & Contact Integration:**
  - Link tickets directly to **Customers (`res.partner`)**, **Sales Orders (`sale.order`)**, **Invoices (`account.move`)**, and **Products (`product.product`)**.
  - One-click **Tickets** smart button on Customer forms and Sales Orders.
* **Resolution Wizard & Printable Service Report:** Record structured root-cause and resolution notes via a dedicated popup wizard and print official **PDF Helpdesk Service Reports**.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 59.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/helpdesk_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'data/helpdesk_data.xml',
        'wizard/helpdesk_ticket_resolve_wizard_views.xml',
        'views/helpdesk_stage_views.xml',
        'views/helpdesk_team_views.xml',
        'views/helpdesk_sla_policy_views.xml',
        'views/helpdesk_ticket_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/helpdesk_menus.xml',
        'report/helpdesk_report.xml',
        'report/helpdesk_report_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


