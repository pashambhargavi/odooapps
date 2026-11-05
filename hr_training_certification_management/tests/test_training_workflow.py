# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class TestTrainingWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Departments
        cls.dept_ops = cls.env['hr.department'].create({
            'name': 'Manufacturing Operations',
        })
        cls.dept_qa = cls.env['hr.department'].create({
            'name': 'Quality Assurance',
        })

        # Job Positions
        cls.job_operator = cls.env['hr.job'].create({
            'name': 'Forklift Equipment Operator',
            'department_id': cls.dept_ops.id,
        })
        cls.job_inspector = cls.env['hr.job'].create({
            'name': 'Quality Control Inspector',
            'department_id': cls.dept_qa.id,
        })

        # Employees
        cls.emp_1 = cls.env['hr.employee'].create({
            'name': 'Operator John Smith',
            'job_id': cls.job_operator.id,
            'department_id': cls.dept_ops.id,
        })
        cls.emp_2 = cls.env['hr.employee'].create({
            'name': 'Operator Sarah Davis',
            'job_id': cls.job_operator.id,
            'department_id': cls.dept_ops.id,
        })
        cls.emp_3 = cls.env['hr.employee'].create({
            'name': 'Inspector Robert Taylor',
            'job_id': cls.job_inspector.id,
            'department_id': cls.dept_qa.id,
        })

        # Mandatory Course for Forklift Operator Job
        cls.course_forklift = cls.env['training.course'].create({
            'name': 'Heavy Equipment Forklift License',
            'code': 'TEST-FORK-01',
            'category': 'technical',
            'validity_months': 12,
            'passing_score': 80.0,
            'duration_hours': 8.0,
            'job_ids': [(4, cls.job_operator.id)],
        })

    def test_01_course_creation_and_validity_math(self):
        """Verify course creation and validation constraints."""
        course = self.course_forklift
        self.assertEqual(course.validity_months, 12)
        self.assertEqual(course.passing_score, 80.0)
        self.assertIn(self.job_operator, course.job_ids)

        # Passing score outside 0-100 should raise ValidationError
        with self.assertRaises(Exception):
            self.env['training.course'].create({
                'name': 'Invalid Course',
                'code': 'ERR-01',
                'passing_score': 150.0,
            })

    def test_02_session_workflow_and_capacity(self):
        """Test session creation, attendee auto-enrollment, and state progression."""
        now = datetime.now()
        session = self.env['training.session'].create({
            'course_id': self.course_forklift.id,
            'start_date': now + timedelta(days=2),
            'end_date': now + timedelta(days=2, hours=8),
            'location': 'Training Bay 4',
            'max_capacity': 10,
        })
        self.assertEqual(session.state, 'draft')

        # Auto-enroll non-compliant staff (emp_1 and emp_2 hold job_operator)
        session.action_auto_enroll_mandatory()
        self.assertGreaterEqual(session.enrolled_count, 2)
        self.assertIn(self.emp_1, session.participation_ids.mapped('employee_id'))

        # State transition: Confirm -> Start
        session.action_confirm()
        self.assertEqual(session.state, 'confirmed')
        session.action_start()
        self.assertEqual(session.state, 'in_progress')

    def test_03_evaluation_and_certificate_issuance(self):
        """Test scoring, certificate number generation, and expiration calculation."""
        part = self.env['training.participation'].create({
            'course_id': self.course_forklift.id,
            'employee_id': self.emp_1.id,
            'attendance_status': 'attended',
            'score': 92.0,
        })
        self.assertEqual(part.evaluation_result, 'passed')

        # Issue certificate
        part.action_issue_certificate()
        self.assertEqual(part.certificate_status, 'valid')
        self.assertTrue(part.certificate_number)
        self.assertTrue(part.certificate_number.startswith('CERT-'))
        self.assertEqual(part.issue_date, date.today())
        
        # Expiry date should be issue_date + 12 months
        expected_expiry = date.today() + relativedelta(months=12)
        self.assertEqual(part.expiry_date, expected_expiry)

        # Smart button on employee
        self.emp_1._compute_training_stats()
        self.assertEqual(self.emp_1.valid_certification_count, 1)

    def test_04_cron_and_expiration_transition(self):
        """Test daily cron marking expiring soon and expired status."""
        today = date.today()
        
        # Case A: Certificate expiring in 15 days -> expiring_soon
        part_expiring = self.env['training.participation'].create({
            'course_id': self.course_forklift.id,
            'employee_id': self.emp_2.id,
            'attendance_status': 'attended',
            'score': 85.0,
            'certificate_status': 'valid',
            'certificate_number': 'CERT-TEST-EXP-01',
            'issue_date': today - relativedelta(months=11, days=15),
        })
        part_expiring._compute_expiry_date()

        # Case B: Certificate expired 5 days ago -> expired
        part_expired = self.env['training.participation'].create({
            'course_id': self.course_forklift.id,
            'employee_id': self.emp_3.id,
            'attendance_status': 'attended',
            'score': 88.0,
            'certificate_status': 'valid',
            'certificate_number': 'CERT-TEST-EXPIRED',
            'issue_date': today - relativedelta(months=13),
        })
        part_expired._compute_expiry_date()

        # Run Cron
        self.env['training.participation']._cron_update_certification_status()

        self.assertEqual(part_expiring.certificate_status, 'expiring_soon')
        self.assertEqual(part_expired.certificate_status, 'expired')

    def test_05_compliance_gap_matrix(self):
        """Test audit gap calculation for job positions with mandatory requirements."""
        # emp_1 is certified valid
        self.env['training.participation'].create({
            'course_id': self.course_forklift.id,
            'employee_id': self.emp_1.id,
            'attendance_status': 'attended',
            'score': 95.0,
            'certificate_status': 'valid',
            'certificate_number': 'CERT-AUDIT-VALID',
            'issue_date': date.today(),
        })

        # emp_2 is in job_operator but has NO certificate (missing gap)
        matrix = self.env['training.compliance.matrix'].create({
            'job_id': self.job_operator.id,
        })
        matrix.action_generate_audit_lines()

        self.assertEqual(matrix.total_requirements, 2)
        self.assertEqual(matrix.compliant_count, 1)
        self.assertEqual(matrix.gap_count, 1)
        self.assertEqual(matrix.compliance_score, 50.0)

        # Check line statuses
        line_emp1 = matrix.line_ids.filtered(lambda l: l.employee_id == self.emp_1)
        line_emp2 = matrix.line_ids.filtered(lambda l: l.employee_id == self.emp_2)
        self.assertEqual(line_emp1.status, 'compliant')
        self.assertEqual(line_emp2.status, 'missing')
