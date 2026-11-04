# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp 1-Click Omnichannel Messaging & Customer Chat Hub',
    'version': '19.0.1.0.0',
    'category': 'Sales/WhatsApp',
    'summary': '1-Click Direct WhatsApp Chat & PDF Sharing for Orders, Invoices, Delivery Slips, Dynamic Templates & Audit Logs (No Meta API Fees Required)',
    'description': """
WhatsApp 1-Click Omnichannel Messaging & Customer Chat Hub for Odoo 19 Community
================================================================================
Empower your sales, accounting, warehouse, and support teams to engage clients instantly on WhatsApp!
Standard Odoo Community has zero WhatsApp capability, while Odoo Enterprise locks WhatsApp behind
expensive Meta Cloud API fees and monthly per-message IAP credits.

This all-in-one hub provides direct 1-click WhatsApp Web, Desktop, and Mobile app messaging
with dynamic templates, automated placeholder replacements, document attachments, and full audit logs
with ZERO mandatory API fees or monthly subscriptions!

Key Features & Business Benefits
---------------------------------
* **1-Click WhatsApp Everywhere:**
  - Share Quotations & Sales Orders directly from `sale.order`.
  - Share Customer Invoices, Overdue Reminders & Payment Receipts from `account.move`.
  - Send Delivery Tracking, Dispatch Notices & Tracking Numbers from `stock.picking`.
  - Direct 1-Click Customer Chat from `res.partner`.
* **Dynamic Template Engine (`whatsapp.template`):**
  - Preconfigured templates for Orders, Invoices, Overdue Alerts, and Delivery updates.
  - Automatic placeholder replacement: `${partner_name}`, `${document_number}`, `${amount_total}`, `${due_date}`, `${company_name}`.
* **Dual Operation Modes:**
  - Direct WhatsApp Web / Mobile Click-to-Chat (Zero cost, works out-of-the-box on browser and phone).
  - Optional Gateway API mode (supports Meta Cloud API, UltraMsg, Twilio, or GreenAPI).
* **Interactive Message Composer Wizard (`whatsapp.composer.wizard`):**
  - Preview formatted message text in real time.
  - Switch templates on the fly, edit custom notes, and verify phone numbers.
* **Comprehensive Audit Trail (`whatsapp.message.log`):**
  - Track message dispatch history, recipient phone, originating user, timestamp, and linked records.
* **100% Free & Open:**
  - No required Meta business verification, no expensive monthly credits.
    """,
    'author': 'Bhargavi Pasham',
    'maintainer': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps/issues/new/choose',
    'license': 'LGPL-3',
    # 'price': 79.00,
    # 'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'sale_management',
        'account',
        'stock',
    ],
    'data': [
        'security/whatsapp_security.xml',
        'security/ir.model.access.csv',
        'data/whatsapp_template_data.xml',
        'wizard/whatsapp_composer_wizard_views.xml',
        'views/whatsapp_template_views.xml',
        'views/whatsapp_message_log_views.xml',
        'views/sale_order_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/res_partner_views.xml',
        'views/whatsapp_menus.xml',
    ],
    'images': [
        'static/description/banner.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
