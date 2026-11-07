# -*- coding: utf-8 -*-
{
    'name': 'Fixed Assets Management & Physical Barcode Audit Pro | Depreciation Schedules, Asset Tracking, Barcode / QR Scanning & Disposal Hub',
    'version': '17.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Enterprise Fixed Assets Accounting, Depreciation Schedules (Straight Line, Declining Balance), Mobile/Laser Barcode QR Audit Scanning, Physical Asset Tracking, Asset Disposal, Revaluation & IFRS/GAAP Compliance',
    'description': """
Enterprise Fixed Assets Management & Physical Barcode Audit Pro
================================================================
Comprehensive, high-performance Fixed Assets Management and Physical Inventory Audit platform engineered for both Odoo Community and Enterprise editions.

Key Functional Innovations:
---------------------------
* **Universal Fixed Asset Register:** Track capital machinery, IT equipment, vehicles, buildings, and intangible assets with asset codes, serial numbers, barcodes, QR codes, custodians, departments, and physical locations.
* **Multi-Method Depreciation Engine:**
  - Straight-Line Depreciation (equal monthly/quarterly/annual split)
  - Declining Balance (Accelerated Degressive with configurable degressive factor)
  - Prorated first-year calculation based on asset acquisition date
  - Automated journal entry posting with balanced debit/credit lines
* **Physical Asset Barcode & QR Audit Sessions:**
  - Launch audit sessions by physical location or asset category
  - High-speed barcode/QR code scanning via mobile camera or laser scanner
  - Instant discrepancy detection: "Verified Present", "Missing / Unaccounted", "Found in Wrong Location", "Unregistered Asset Found"
  - One-click discrepancy reconciliation and location auto-update
* **Asset Lifecycle Management:**
  - Asset Revaluation & Impairment Accounting
  - Internal Custodian & Location Transfers
  - Asset Retirement / Disposal / Sale with automated Gain/Loss on Disposal computation
* **Audit Labels & Boardroom Reporting:**
  - Printable Asset Barcode & QR Code Label Sheets
  - Executive QWeb PDF Fixed Asset Depreciation Schedule & Net Book Value (NBV) Ledger
  - Asset Audit Discrepancy Reconciliation Statement
* **Multi-Company Security & Audit Trail:** Full support for multi-company isolation with immutable chatter logs.
    """,
    'author': 'Bhargavi Pasham',
    'support': 'bhargavipasham2000@gmail.com',
    'license': 'LGPL-3',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'depends': ['base', 'account', 'mail'],
    'data': [
        'security/asset_security.xml',
        'security/ir.model.access.csv',
        'data/asset_sequence.xml',
        'views/account_asset_category_views.xml',
        'views/account_asset_views.xml',
        'views/asset_audit_session_views.xml',
        'views/asset_disposal_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/menu_views.xml',
        'report/asset_reports.xml',
        'report/asset_barcode_labels.xml',
        'report/asset_depreciation_report.xml',
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
