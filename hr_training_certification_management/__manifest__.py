# -*- coding: utf-8 -*-
{
    'name': 'Training & Certification Management (Compliance Matrix, OSHA/GMP Tracking & Digital Certificates)',
    'version': '17.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Mandatory Compliance Training Matrix, Certification Renewals, OSHA/GMP Tracking, Skill Badges & Digital Certificate Issuance',
    'description': """
Training & Certification Management Hub
======================================
Comprehensive Enterprise Compliance Training, Mandatory Job Qualification Matrix & Digital Certificate Lifecycle for Odoo Community.

Key Features:
-------------
* **Mandatory Compliance Matrix**: Link required courses directly to Job Positions and Departments (OSHA, GMP, Forklift licenses, ISO 9001, Cleanroom).
* **Gap Analysis & Audit Tool**: 1-Click audit calculating compliance percentages and highlighting non-certified personnel gaps.
* **Training Sessions & Batches**: Schedule in-person, online, or hybrid sessions with maximum capacity constraints and 1-click non-compliant auto-enrollment.
* **Automated Expiry & Renewal Reminders**: Computes expiration dates from course validity months, flagging certifications expiring within 30 days.
* **Evaluation & Scoring Engine**: Record attendee attendance and test scores with configurable passing thresholds.
* **Printable Digital Certificate PDF**: High-definition landscape certificate with verification codes, regulatory details, and 3-signatory lines.
* **Employee Compliance Dashboard**: Smart button and alert banners on employee profiles warning of expiring or missing credentials.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    'support': 'bhargavipasham2000@gmail.com',
    # 'price': 179.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'mail'],
    'data': [
        'security/hr_training_security.xml',
        'security/ir.model.access.csv',
        'data/hr_training_sequence_data.xml',
        'data/hr_training_cron_data.xml',
        'data/hr_training_demo_data.xml',
        'views/training_course_views.xml',
        'views/training_session_views.xml',
        'views/training_participation_views.xml',
        'views/training_compliance_matrix_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_training_menus.xml',
        'report/hr_training_certificate_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}


