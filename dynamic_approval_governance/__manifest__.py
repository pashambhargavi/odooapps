# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Multi-Tier Approval Matrix & Workflow Governance',
    'version': '17.0.1.0.0',
    'category': 'Productivity',
    'summary': 'Dynamic Multi-Tier Approval Matrix for Sales, Purchases, Invoices & Internal Requests',
    'description': """
Multi-Tier Approval Matrix & Workflow Governance for Odoo 18 Community
======================================================================
Bring enterprise-grade approval workflows and transaction governance to Odoo 18 Community Edition:

Key Features
------------
* **Standalone Approval Requests & Categories:** Create customizable approval categories (Expense, Travel, Procurement, Contract Sign-Off, Payment Release, General) with configurable required/optional fields (Date, Period, Amount, Quantity, Partner, Reference, Location, Product Items).
* **Multi-Level Sequential & Parallel Approval Chains:** Configure multi-step approval tiers with specific users, minimum required approvers, and sequential or parallel enforcement.
* **Dynamic Approval Matrix for Sales, Purchases & Accounting:**
  - **Sales Orders (`sale.order`):** Automatically route orders for multi-tier approval based on Total Amount or Maximum Line Discount %.
  - **Purchase Orders (`purchase.order`):** Enforce multi-tier budget sign-off based on Untaxed/Total Order Amount before PO confirmation.
  - **Invoices & Vendor Bills (`account.move`):** Gate Customer Invoices and Vendor Bills before posting based on financial thresholds.
* **Mandatory Rejection Reason Wizard & Full Audit Trail:** Capture structured rejection reasons in chatter, schedule automated To-Do activities for approvers, and print official **PDF Approval Certificates**.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 49.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'purchase',
        'account',
    ],
    'data': [
        'security/approval_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/approval_category_data.xml',
        'wizard/approval_reject_wizard_views.xml',
        'views/approval_category_views.xml',
        'views/approval_request_views.xml',
        'views/approval_matrix_rule_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/account_move_views.xml',
        'views/approval_menus.xml',
        'report/approval_report.xml',
        'report/approval_report_templates.xml',
    ],
    'demo': [
        'demo/approval_demo.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

