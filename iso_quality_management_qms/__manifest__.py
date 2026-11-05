# -*- coding: utf-8 -*-
{
    'name': 'ISO 9001:2015 Quality Management System (QMS, NCR, CAPA & 8D Hub)',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing/Quality',
    'summary': 'Enterprise ISO 9001:2015, IATF 16949 & AS9100 QMS: Non-Conformance Reports (NCR), 8D CAPA, 5-Whys, Fishbone, Audits & FMEA Risk Matrix',
    'description': """
ISO 9001:2015 Quality Management System (QMS & CAPA Hub)
=========================================================
Enterprise Quality Assurance, Non-Conformance Management & Root-Cause Corrective Actions for Odoo Community.

Key Features:
-------------
* **Non-Conformance Reporting (NCR)**: Manage internal defects, customer returns, and supplier reject workflows.
* **ISO 9001 Clause 10.2 / 8D CAPA Engine**: Full 8 Disciplines methodology (D1 Team, D2 Problem, D3 Containment, D4 Root Cause, D5 Actions, D6 Verification, D7 Prevention, D8 Closure).
* **Interactive Root-Cause Investigation**: 5-Whys questionnaire and Ishikawa Fishbone categories (Man, Machine, Material, Method, Measurement, Milieu).
* **Failure Mode & Effects Analysis (FMEA / RPN)**: Severity, Occurrence, Detection matrix with before/after RPN scores.
* **ISO Quality Audits & Checklists**: Conduct internal, supplier, and certification audits with automated NCR triggering.
* **Smart Integration**: Direct smart buttons on Receipts (stock.picking), Purchases (purchase.order), and Sales (sale.order).
* **Printable Executive 8D Investigation Report**: Professional QWeb PDF for customer complaints and auditor reviews.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    # 'price': 299.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'stock', 'purchase', 'sale_management'],
    'data': [
        'security/qms_security.xml',
        'security/ir.model.access.csv',
        'data/qms_sequence_data.xml',
        'views/qms_ncr_views.xml',
        'views/qms_capa_views.xml',
        'views/qms_audit_views.xml',
        'views/qms_risk_views.xml',
        'views/qms_integration_views.xml',
        'views/qms_menus.xml',
        'report/qms_8d_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
