# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestShiftRosterWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.department = cls.env['hr.department'].create({
            'name': 'Emergency Care Unit',
        })
        cls.employee_1 = cls.env['hr.employee'].create({
            'name': 'Nurse Alex Morgan',
            'department_id': cls.department.id,
            'weekly_max_hours': 40.0,
        })
        cls.employee_2 = cls.env['hr.employee'].create({
            'name': 'Nurse Ben Davies',
            'department_id': cls.department.id,
            'weekly_max_hours': 40.0,
        })

        cls.shift_day = cls.env['hr.shift.template'].create({
            'name': 'Standard Day Shift',
            'code': 'DAY-08',
            'shift_type': 'day',
            'start_time': 8.0,
            'end_time': 16.5,
            'break_duration': 0.5,
            'differential_rate': 0.0,
            'required_headcount': 1,
            'department_ids': [(4, cls.department.id)],
        })

        cls.shift_night = cls.env['hr.shift.template'].create({
            'name': 'Overnight Emergency Shift',
            'code': 'NGT-22',
            'shift_type': 'night',
            'start_time': 22.0,
            'end_time': 6.0,
            'break_duration': 0.5,
            'differential_rate': 20.0,
            'required_headcount': 1,
            'department_ids': [(4, cls.department.id)],
        })

    def test_01_shift_template_duration_math(self):
        """Test calculation of shift working hours including midnight crossing."""
        # Day shift: 16.5 - 8.0 - 0.5 = 8.0 hours
        self.assertEqual(self.shift_day.duration_hours, 8.0)

        # Overnight shift: (24 - 22 + 6) - 0.5 = 7.5 hours
        self.assertEqual(self.shift_night.duration_hours, 7.5)

    def test_02_roster_generation_and_auto_scheduling(self):
        """Test generating slots across dates and auto-scheduling department staff."""
        d_start = fields.Date.today()
        d_end = d_start + timedelta(days=2)

        roster = self.env['hr.shift.roster'].create({
            'title': '3-Day Emergency Roster',
            'department_id': self.department.id,
            'date_start': d_start,
            'date_end': d_end,
        })
        self.assertTrue(roster.name.startswith('RST/'))

        # Generate slots
        roster.action_generate_slots()
        self.assertGreater(roster.total_shifts_count, 0)
        self.assertEqual(roster.unassigned_shifts_count, roster.total_shifts_count)

        # Run auto-scheduling
        roster.action_auto_schedule()
        self.assertEqual(roster.unassigned_shifts_count, 0)
        self.assertGreater(roster.total_shifts_count, 0)

        # Submit and publish roster
        roster.action_confirm()
        roster.action_publish()
        self.assertEqual(roster.state, 'published')

    def test_03_conflict_detection_double_booking(self):
        """Test schedule conflict detection when same employee is assigned twice on same date."""
        today = fields.Date.today()
        roster = self.env['hr.shift.roster'].create({
            'title': 'Conflict Test Roster',
            'department_id': self.department.id,
            'date_start': today,
            'date_end': today,
        })
        # Create 2 shifts on same date for employee_1
        shift1 = self.env['hr.shift.schedule'].create({
            'roster_id': roster.id,
            'shift_template_id': self.shift_day.id,
            'employee_id': self.employee_1.id,
            'date': today,
        })
        shift2 = self.env['hr.shift.schedule'].create({
            'roster_id': roster.id,
            'shift_template_id': self.shift_night.id,
            'employee_id': self.employee_1.id,
            'date': today,
        })

        # Scan for conflicts
        roster.action_check_conflicts()
        self.assertTrue(shift1.has_conflict)
        self.assertTrue(shift2.has_conflict)
        self.assertEqual(roster.conflict_count, 2)

    def test_04_open_shift_bidding_and_confirmation(self):
        """Test open shift pool and employee attendance confirmation."""
        shift = self.env['hr.shift.schedule'].create({
            'shift_template_id': self.shift_day.id,
            'date': fields.Date.today(),
            'employee_id': False,
        })
        self.assertTrue(shift.is_open_shift)

        # Assign employee
        shift.write({'employee_id': self.employee_2.id})
        self.assertFalse(shift.is_open_shift)

        # Confirm shift
        shift.action_confirm_attendance()
        self.assertEqual(shift.state, 'confirmed')

    def test_05_peer_shift_swap_workflow(self):
        """Test peer shift trade between Nurse Alex and Nurse Ben with manager approval."""
        shift_alex = self.env['hr.shift.schedule'].create({
            'shift_template_id': self.shift_day.id,
            'employee_id': self.employee_1.id,
            'date': fields.Date.today() + timedelta(days=1),
            'state': 'scheduled',
        })

        # Alex requests to swap with Ben
        swap = self.env['hr.shift.swap.request'].create({
            'requesting_employee_id': self.employee_1.id,
            'original_shift_id': shift_alex.id,
            'swap_type': 'peer',
            'target_employee_id': self.employee_2.id,
            'reason': 'Family emergency requirement on shift date',
        })
        self.assertTrue(swap.name.startswith('SWP/'))
        self.assertEqual(swap.state, 'draft')

        # Ben agrees
        swap.action_peer_accept()
        self.assertEqual(swap.state, 'peer_accepted')

        # Manager approves
        swap.action_manager_approve()
        self.assertEqual(swap.state, 'manager_approved')

        # Verify shift is now assigned to Nurse Ben!
        self.assertEqual(shift_alex.employee_id.id, self.employee_2.id)
        self.assertEqual(shift_alex.state, 'swapped')
