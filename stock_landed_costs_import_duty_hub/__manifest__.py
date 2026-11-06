# -*- coding: utf-8 -*-
{
    'name': 'Landed Costs & Multi-Currency Import Duty Hub | Freight, Customs, Clearing & COGS Allocation',
    'version': '15.0.1.0.0',
    'category': 'Inventory/Landed Costs',
    'summary': 'Allocate international sea/air freight, customs import duties, terminal handling (THC), and clearance fees across incoming receipts in Odoo Community & Enterprise.',
    'description': """
Landed Costs & Multi-Currency Import Duty Hub
=============================================
Complete enterprise landed cost allocation suite for Odoo Community and Enterprise. Bring true Cost of Goods Sold (COGS) visibility to your inventory by factoring in all import charges, freight costs, and customs tariffs.

Key Capabilities:
-----------------
* Multi-Method Cost Allocation: Equal, By Quantity, By Current Value, By Gross Weight, or By Volume.
* Multi-Currency Import Duty: Invoice freight or customs in foreign currencies (USD, EUR, GBP, AED, CNY) with automated exchange rate conversion.
* 1-Click Integration with Vendor Bills: Link freight bills directly to accounting vouchers.
* Direct Receipt Picking Selection: Attach multiple incoming receipts to a single container landed cost document.
* Automated Inventory Revaluation: Updates product unit standard_price and posts accounting valuation adjustments.
* Printable Landed Cost Audit Voucher: Professional PDF summary for customs audits, tax inspections, and landed cost reconciliation.
* 100% Native Architecture, Zero Third-Party Dependencies.
    """,
    'author': 'Bhargavi Pasham',
    'support': 'bhargavipasham2000@gmail.com',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'license': 'OPL-1',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'depends': [
        'base',
        'stock',
        'account',
        'mail',
    ],
    'data': [
        'security/landed_cost_security.xml',
        'security/ir.model.access.csv',
        'data/landed_cost_data.xml',
        'views/stock_landed_cost_hub_views.xml',
        'views/stock_picking_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'report/landed_cost_report.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
