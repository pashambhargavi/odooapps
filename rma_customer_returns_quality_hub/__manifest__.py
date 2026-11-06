# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'RMA, Customer Returns & Quality Inspection Hub',
    'version': '16.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'End-to-End RMA Return Merchandise Authorization, Quality Inspection, Automated Credit Notes, Replacement Deliveries & Printable Return Slips for Odoo Community',
    'description': """
RMA, Customer Returns & Quality Inspection Hub for Odoo 18 Community
===================================================================
Standard Odoo Community lacks a dedicated Return Merchandise Authorization (RMA) workflow.
This comprehensive hub empowers support, warehouse, and accounting teams with:

* **Complete 5-Stage RMA Lifecycle:** Draft -> Approved -> Goods Received -> Inspected -> Resolved / Closed.
* **1-Click Generation from Orders & Invoices:** Instant ticket creation from Sales Orders, Delivery Orders, and Customer Invoices.
* **Dedicated Quality Inspection Workbench:** Inspect returned goods with Pass, Restock, Repair, Scrap, or Return-to-Vendor dispositions.
* **Automated Financial & Stock Reconciliation:** 1-Click customer refund credit note generation (`account.move`) and warranty replacement delivery (`stock.picking`).
* **Printable Customer Return Slip (PDF):** Formal shipping slip with return instructions and tracking barcodes.
* **Multi-Company & Multi-Currency Ready:** Full enterprise security isolation and chatter tracking.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 99.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'stock',
        'account',
    ],
    'data': [
        'security/rma_security.xml',
        'security/ir.model.access.csv',
        'data/rma_sequence_data.xml',
        'data/rma_reason_data.xml',
        'report/rma_report.xml',
        'wizard/rma_inspection_wizard_views.xml',
        'views/rma_reason_views.xml',
        'views/rma_order_views.xml',
        'views/sale_order_views.xml',
        'views/stock_picking_views.xml',
        'views/account_move_views.xml',
        'views/rma_menus.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}


