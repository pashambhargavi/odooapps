# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestHrGratuityWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Employee
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Ahmed Al-Mansoor',
            'work_email': 'ahmed@example.com',
            'company_id': cls.company.id,
        })

        # UAE Rule
        cls.rule_uae = cls.env['hr.gratuity.rule'].create({
            'name': 'Test UAE Rule',
            'code': 'TEST_UAE',
            'wage_type': 'basic',
            'monthly_days_divisor': 30.0,
            'min_service_days': 365,
            'first_period_years': 5.0,
            'first_period_days_per_year': 21.0,
            'subsequent_days_per_year': 30.0,
            'max_gratuity_years_cap': 2.0,
            'resignation_rule_type': 'equal',
            'company_id': cls.company.id,
        })

        # KSA Rule
        cls.rule_ksa = cls.env['hr.gratuity.rule'].create({
            'name': 'Test KSA Rule',
            'code': 'TEST_KSA',
            'wage_type': 'basic',
            'monthly_days_divisor': 30.0,
            'min_service_days': 365,
            'first_period_years': 5.0,
            'first_period_days_per_year': 15.0,
            'subsequent_days_per_year': 30.0,
            'max_gratuity_years_cap': 0.0,
            'resignation_rule_type': 'ksa_tiered',
            'tier1_max_years': 2.0,
            'tier1_percentage': 0.0,
            'tier2_max_years': 5.0,
            'tier2_percentage': 33.33,
            'tier3_max_years': 10.0,
            'tier3_percentage': 66.67,
            'tier4_percentage': 100.0,
            'company_id': cls.company.id,
        })

    def test_01_uae_labor_law_calculation(self):
        """Verify 4 years service under UAE Decree 33/2021."""
        today = date.today()
        # 4 years tenure exactly: 4 * 365 days
        joining = today - timedelta(days=1461)

        settlement = self.env['hr.gratuity.settlement'].create({
            'employee_id': self.employee.id,
            'joining_date': joining,
            'leaving_date': today,
            'departure_reason': 'resignation',
            'gratuity_rule_id': self.rule_uae.id,
            'basic_salary': 6000.0,
            'company_id': self.company.id,
        })

        settlement.action_calculate_gratuity()
        self.assertEqual(settlement.daily_wage, 200.0)
        self.assertGreaterEqual(settlement.service_years, 3.99)
        # 4 years * 21 days * 200 daily wage = ~16,800
        self.assertAlmostEqual(settlement.gratuity_amount, 16800.0, delta=200.0)
        self.assertEqual(settlement.state, 'calculated')

    def test_02_ksa_labor_law_tiered_resignation(self):
        """Verify Saudi Labor Law Article 85 resignation reduction."""
        today = date.today()
        # 3.5 years tenure
        joining = today - timedelta(days=1278)

        settlement = self.env['hr.gratuity.settlement'].create({
            'employee_id': self.employee.id,
            'joining_date': joining,
            'leaving_date': today,
            'departure_reason': 'resignation',
            'gratuity_rule_id': self.rule_ksa.id,
            'basic_salary': 3000.0,
            'company_id': self.company.id,
        })

        settlement.action_calculate_gratuity()
        self.assertEqual(settlement.daily_wage, 100.0)
        # Under KSA: 3.5 yrs * 15 days = 52.5 days * 100 = 5,250 full base.
        # Resignation between 2 and 5 years gets 33.33%: 5250 * 0.3333 = ~1,750
        self.assertAlmostEqual(settlement.gratuity_amount, 1750.0, delta=50.0)

    def test_03_full_settlement_components(self):
        """Verify leave encashment, pending days, air ticket, and loan deductions."""
        today = date.today()
        settlement = self.env['hr.gratuity.settlement'].create({
            'employee_id': self.employee.id,
            'joining_date': today - timedelta(days=1461),
            'leaving_date': today,
            'departure_reason': 'termination',
            'gratuity_rule_id': self.rule_uae.id,
            'basic_salary': 6000.0,
            'unused_leave_days': 10.0,
            'pending_salary_days': 5.0,
            'air_ticket_amount': 800.0,
            'loan_deduction': 1500.0,
            'company_id': self.company.id,
        })

        settlement.action_calculate_gratuity()
        self.assertEqual(settlement.leave_salary_encashment, 2000.0)
        self.assertEqual(settlement.pending_salary_amount, 1000.0)
        self.assertEqual(settlement.air_ticket_amount, 800.0)
        self.assertEqual(settlement.total_deductions, 1500.0)

        # Expected net: Gratuity (~16,800) + 2000 + 1000 + 800 - 1500 = ~19,100
        expected_net = settlement.total_entitlements - settlement.total_deductions
        self.assertEqual(settlement.net_payable, expected_net)

    def test_04_department_clearance_workflow(self):
        """Verify clearance checkboxes and transition to cleared and approved."""
        today = date.today()
        settlement = self.env['hr.gratuity.settlement'].create({
            'employee_id': self.employee.id,
            'joining_date': today - timedelta(days=1461),
            'leaving_date': today,
            'departure_reason': 'termination',
            'gratuity_rule_id': self.rule_uae.id,
            'basic_salary': 6000.0,
            'company_id': self.company.id,
        })
        settlement.action_calculate_gratuity()

        # Attempt clearance without all checkboxes
        with self.assertRaises(UserError):
            settlement.action_sign_clearance()

        # Check all 4 departments
        settlement.write({
            'clearance_it': True,
            'clearance_finance': True,
            'clearance_admin': True,
            'clearance_hr': True,
        })
        self.assertTrue(settlement.all_cleared)

        settlement.action_sign_clearance()
        self.assertEqual(settlement.state, 'cleared')

        settlement.action_approve()
        self.assertEqual(settlement.state, 'approved')

    def test_05_employee_settlement_counter(self):
        """Verify employee smart button count."""
        today = date.today()
        settlement = self.env['hr.gratuity.settlement'].create({
            'employee_id': self.employee.id,
            'joining_date': today - timedelta(days=1461),
            'leaving_date': today,
            'departure_reason': 'termination',
            'gratuity_rule_id': self.rule_uae.id,
            'basic_salary': 6000.0,
            'company_id': self.company.id,
        })
        self.employee._compute_gratuity_settlement_count()
        self.assertGreaterEqual(self.employee.gratuity_settlement_count, 1)
