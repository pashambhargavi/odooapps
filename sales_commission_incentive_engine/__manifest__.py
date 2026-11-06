# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales Commission, Multi-Tier Incentive & Partner Affiliate Hub',
    'version': '14.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Dynamic Sales Rep Commissions, Manager Overrides, Margin-Based Incentives, Worksheets & Automated Vendor Bill Settlement',
    'description': """
Sales Commission, Multi-Tier Incentive & Partner Affiliate Hub for Odoo 18 Community
=====================================================================================
Eliminate manual Excel calculations. Reward your sales teams, managers, and external referral agents with automated, transparent, and multi-tier commission management:

Key Features
------------
* **Versatile Commission Plan Engine:**
  - Revenue-Based (% of Order or Invoice Amount).
  - Cash Collection-Based (% of Paid Customer Invoices only - prevent paying commissions on bad debt).
  - Profit Margin-Based (% of Gross Margin, incentivizing sales reps to protect selling prices).
  - Progressive Volume Tiers (e.g. 0-$10k @ 3%, $10k-$50k @ 5%, >$50k @ 8%).
* **Multi-Tier Hierarchy & Manager Overrides:**
  - Direct Sales Rep Commission.
  - Sales Manager Override Commission on team volume.
  - External Referral Agent / Affiliate Partner commissions.
* **Automated Commission Worksheets (`commission.worksheet`):**
  - Group and review commissions by Month, Quarter, or Custom Period.
  - Approval workflow: Draft -> Calculated -> Manager Approved -> Settled.
* **1-Click Vendor Bill Settlement:**
  - Automatically generate a posted Vendor Bill for external contractors / agents or export approved payroll records.
* **Visual PDF Commission Statement & Audit Report:**
  - Print itemized commission statements with order references, line amounts, margin % and manager sign-off.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 69.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/commission_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/commission_plan_data.xml',
        'wizard/commission_make_invoice_wizard_views.xml',
        'views/commission_plan_views.xml',
        'views/commission_worksheet_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/commission_menus.xml',
        'report/commission_report.xml',
        'report/commission_report_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}




