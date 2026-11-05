# -*- coding: utf-8 -*-
{
    'name': 'Employee Shift Scheduling, Duty Roster & Attendance Planning Hub',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Employees',
    'summary': 'Enterprise Visual Shift Planner, Weekly/Monthly Duty Rosters, Conflict Detection, Open Shift Bidding, Shift Swaps & Overtime Differential Pay',
    'description': """
Employee Shift Scheduling & Duty Roster Management Hub
======================================================
Comprehensive Shift Planning, Multi-Branch Rostering and Peer Shift-Swap Marketplace for Odoo Community.

Key Features:
-------------
* **Visual Duty Roster & Master Planner**: Build weekly, bi-weekly, or monthly shift rosters with department filtering.
* **Shift Templates & Differentials**: Pre-configure Morning, Afternoon, Night, and Split shifts with night/weekend differential pay rates.
* **Smart Conflict & Overlap Detection**: Instant alerts for overlapping shifts, excessive consecutive work days, and weekly hour limit violations.
* **Auto-Scheduling Engine**: Automatically assigns qualified available personnel to unfilled shifts based on department and skills.
* **Open Shift Bidding & Peer Swapping**: Employees can request shift swaps with colleagues or release shifts to the open bidding pool with manager approval.
* **Printable Duty Roster Matrix PDF**: Clean executive schedule sheet with daily assignments, hours tally, and manager sign-off.
    """,
    'author': 'Bhargavi Pasham',
    'website': 'https://github.com/pashambhargavi/odooapps',
    # 'price': 199.00,
    # 'currency': 'EUR',
    'license': 'LGPL-3',
    'depends': ['base', 'hr', 'resource', 'mail'],
    'data': [
        'security/hr_shift_security.xml',
        'security/ir.model.access.csv',
        'data/hr_shift_sequence_data.xml',
        'data/hr_shift_demo_templates.xml',
        'views/hr_shift_template_views.xml',
        'views/hr_shift_schedule_views.xml',
        'views/hr_shift_roster_views.xml',
        'views/hr_shift_swap_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_shift_menus.xml',
        'report/hr_shift_roster_report.xml',
    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
