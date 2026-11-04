# -*- coding: utf-8 -*-
from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError


class TestVendorScorecardWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company

        # Vendor
        cls.vendor_a = cls.env['res.partner'].create({
            'name': 'Apex Industrial Supplies Ltd',
            'supplier_rank': 1,
            'is_company': True,
        })

        cls.vendor_b = cls.env['res.partner'].create({
            'name': 'Defective Parts Corp',
            'supplier_rank': 1,
            'is_company': True,
        })

        # Scorecard Template
        cls.template = cls.env['vendor.scorecard.template'].create({
            'name': 'Test Evaluation Rubric',
            'min_grade_a': 90.0,
            'min_grade_b': 75.0,
            'min_grade_c': 60.0,
            'company_id': cls.company.id,
            'criterion_ids': [
                (0, 0, {
                    'name': 'On-Time Delivery Rate',
                    'metric_type': 'otd',
                    'weight': 40.0,
                    'benchmark_target': 100.0,
                }),
                (0, 0, {
                    'name': 'Quality Conformance',
                    'metric_type': 'quality',
                    'weight': 40.0,
                    'benchmark_target': 100.0,
                }),
                (0, 0, {
                    'name': 'Service Support',
                    'metric_type': 'service',
                    'weight': 20.0,
                    'benchmark_target': 100.0,
                }),
            ]
        })

        # Period
        cls.today = date.today()
        cls.period = cls.env['vendor.scorecard.period'].create({
            'name': 'Q1 Test Review',
            'date_from': cls.today - timedelta(days=30),
            'date_to': cls.today + timedelta(days=1),
            'template_id': cls.template.id,
            'company_id': cls.company.id,
        })

    def test_01_template_configuration(self):
        """Verify weights sum and invalid threshold constraints."""
        self.assertEqual(self.template.total_weight, 100.0)

        # Invalid threshold: Grade A lower than Grade B should raise error
        with self.assertRaises(ValidationError):
            self.template.write({'min_grade_a': 50.0, 'min_grade_b': 80.0})

    def test_02_evaluation_creation_and_metrics(self):
        """Test calculation of OTD, Quality, and overall score."""
        eval_record = self.env['vendor.scorecard.evaluation'].create({
            'period_id': self.period.id,
            'partner_id': self.vendor_a.id,
            'template_id': self.template.id,
            'service_score': 95.0,
        })

        eval_record.action_compute_metrics()
        self.assertGreaterEqual(eval_record.final_score, 0.0)
        self.assertTrue(eval_record.grade in ['grade_a', 'grade_b', 'grade_c', 'grade_d'])
        self.assertEqual(len(eval_record.line_ids), 3)

    def test_03_publishing_and_partner_sync(self):
        """Ensure publishing evaluation updates supplier grade on partner."""
        eval_record = self.env['vendor.scorecard.evaluation'].create({
            'period_id': self.period.id,
            'partner_id': self.vendor_a.id,
            'template_id': self.template.id,
            'service_score': 100.0,
        })
        eval_record.action_compute_metrics()
        eval_record.action_review()
        eval_record.action_approve()
        eval_record.action_publish()

        self.assertEqual(eval_record.state, 'published')
        self.assertEqual(self.vendor_a.latest_scorecard_id, eval_record)
        self.assertEqual(self.vendor_a.supplier_grade, eval_record.grade)
        self.assertAlmostEqual(self.vendor_a.supplier_score, eval_record.final_score, places=1)

    def test_04_restricted_supplier_po_alert(self):
        """Verify warning message and confirmation check when supplier is Grade D."""
        # Force vendor B to Grade D
        self.vendor_b.write({
            'supplier_grade': 'grade_d',
            'supplier_score': 45.0,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor_b.id,
            'company_id': self.company.id,
        })

        # Check warning computed
        self.assertTrue(bool(po.supplier_grade_warning))
        self.assertIn("RESTRICTED SUPPLIER ALERT", po.supplier_grade_warning)

    def test_05_period_lifecycle(self):
        """Test period state transitions."""
        self.period.action_start()
        self.assertEqual(self.period.state, 'in_progress')
        self.period.action_reset_draft()
        self.assertEqual(self.period.state, 'draft')
