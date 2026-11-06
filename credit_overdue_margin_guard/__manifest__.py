# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Customer Credit, Overdue Aging & Margin Risk Guard',
    'version': '15.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Enforce Customer Credit Limits, Overdue Invoice Aging Blocks, Minimum Profit Margin % & Finance Override Workflows',
    'description': """
Customer Credit, Overdue Aging & Margin Risk Guard for Odoo 18 Community
========================================================================
Protect your company's cash flow and profit margins in Odoo 18 Community Edition with automated 4-point commercial risk controls:

Key Features
------------
* **4-Point Commercial Risk Engine on Sales Orders:**
  1. **Manual Credit Hold Freeze:** Instantly freeze orders for high-risk or disputed customer accounts.
  2. **Total Credit Exposure Limit:** Evaluates Unpaid Posted Invoices + Uninvoiced Confirmed Sales Orders + Current Quotation Total against the customer's credit limit.
  3. **Overdue Invoice Aging Gate:** Blocks order confirmation when a customer has unpaid invoices exceeding the maximum allowed overdue days (e.g., > 30 days past due) or maximum overdue invoice count.
  4. **Minimum Profit Margin % Guard:** Calculates real-time Unit Cost, Margin Amount, and Margin % on every Sales Order line and blocks orders that fall below the minimum required profit margin %.
* **Configurable Risk Policies Tiers:** Assign reusable Credit & Margin Risk Tiers (e.g., *Standard B2B Tier*, *VIP Enterprise Tier*, *Strict Cash-On-Delivery Tier*) or customize thresholds per customer.
* **Structured Finance Override Workflow:** When a Sales Order violates credit, aging, or margin rules, salespeople can request a **Credit & Margin Exception (`credit.override.request`)** for one-click approval or rejection by Credit Controllers.
* **Customer Credit & Aging Risk Statement PDF:** Print a comprehensive PDF Credit Exposure & Overdue Aging Statement directly from any Customer or Override Request.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 54.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
    ],
    'data': [
        'security/credit_guard_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/credit_policy_data.xml',
        'wizard/credit_override_reject_wizard_views.xml',
        'views/credit_risk_policy_views.xml',
        'views/credit_override_request_views.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
        'views/credit_guard_menus.xml',
        'report/credit_guard_report.xml',
        'report/credit_guard_report_templates.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}



