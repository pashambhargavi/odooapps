# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError
from odoo import fields

class TestQmsWorkflow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({
            'name': 'Precision Aero Parts Inc.',
            'supplier_rank': 1,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Titanium Hydraulic Coupling X9',
            'type': 'consu',
            'standard_price': 120.0,
            'list_price': 250.0,
        })
        cls.qa_user = cls.env['res.users'].create({
            'name': 'Sarah Connor (QA Engineer)',
            'login': 'sarah_qa_test',
            'email': 'sarah@test.com',
        })
        cls.env.ref('iso_quality_management_qms.group_qms_user').users = [(4, cls.qa_user.id)]

    def test_01_ncr_lifecycle_and_quarantine(self):
        """Test complete NCR creation, review, quarantine, and closing."""
        ncr = self.env['qms.ncr'].create({
            'title': 'Outer Diameter Micron Runout Exceeded',
            'source_type': 'internal',
            'product_id': self.product.id,
            'qty_affected': 50.0,
            'qty_rejected': 12.0,
            'severity': 'major',
            'detection_stage': 'in_process',
            'description': 'Machining runout measured at 0.045mm exceeding specification of 0.015mm.',
            'containment_action': 'Physical red quarantine hold tags affixed; line CNC-04 paused.',
            'disposition': 'rework',
        })
        self.assertTrue(ncr.name.startswith('NCR/'), "NCR Reference sequence must start with 'NCR/'")
        self.assertEqual(ncr.state, 'draft')

        # Submit for QA review
        ncr.action_submit()
        self.assertEqual(ncr.state, 'under_review')

        # Quarantine stock
        ncr.action_quarantine()
        self.assertEqual(ncr.state, 'quarantined')

        # Close NCR
        ncr.action_close()
        self.assertEqual(ncr.state, 'closed')
        self.assertTrue(ncr.close_date)

    def test_02_ncr_trigger_8d_capa(self):
        """Test triggering an 8D CAPA directly from a quarantined NCR."""
        ncr = self.env['qms.ncr'].create({
            'title': 'Customer Leakage Complaint - High Pressure Joint',
            'source_type': 'customer',
            'partner_id': self.partner.id,
            'product_id': self.product.id,
            'severity': 'critical',
            'description': 'Customer reported fluid seepage at 250 bar pressure testing.',
            'containment_action': 'Quarantined remaining 120 units in warehouse; customer shipment recalled.',
        })
        ncr.action_submit()
        ncr.action_quarantine()

        # Trigger CAPA
        action = ncr.action_create_capa()
        capa_id = action['res_id']
        capa = self.env['qms.capa'].browse(capa_id)

        self.assertEqual(ncr.state, 'capa_required')
        self.assertEqual(ncr.capa_count, 1)
        self.assertEqual(capa.ncr_id.id, ncr.id)
        self.assertTrue(capa.name.startswith('CAPA/'))
        self.assertEqual(capa.state, 'd1_team')

    def test_03_8d_capa_root_cause_and_rpn_reduction(self):
        """Test 8D problem solving methodology, 5-Whys, Ishikawa, and RPN calculation."""
        capa = self.env['qms.capa'].create({
            'title': 'Casting Porosity Elimination Initiative',
            'capa_type': 'corrective',
            'source': 'customer_complaint',
            'product_id': self.product.id,
            'assigned_to_id': self.qa_user.id,
            'problem_statement': 'Sub-surface micro-porosity discovered after anodizing process on 8% of batches.',
            'containment_actions': '100% Eddy Current non-destructive inspection gate placed before final packing.',
            'initial_severity': 8,
            'initial_occurrence': 6,
            'initial_detection': 5,
        })
        # Initial RPN: 8 * 6 * 5 = 240
        self.assertEqual(capa.initial_rpn, 240)

        # Advance D1 -> D2 -> D3 -> D4
        capa.action_advance_stage()  # to d2_problem
        self.assertEqual(capa.state, 'd2_problem')
        capa.action_advance_stage()  # to d3_containment
        self.assertEqual(capa.state, 'd3_containment')
        capa.action_advance_stage()  # to d4_root_cause
        self.assertEqual(capa.state, 'd4_root_cause')

        # 5-Whys analysis
        capa.write({
            'why_1': 'Gas trapped in aluminum melt during die casting.',
            'why_2': 'Degassing nitrogen lance pressure dropped below 4.2 bar.',
            'why_3': 'Lance regulator diaphragm experienced premature fatigue tear.',
            'why_4': 'Preventive maintenance interval was set at 12 months instead of 3 months.',
            'why_5': 'Supplier PM schedule not synchronized with high-frequency casting run rates.',
            'root_cause_summary': 'Insufficient degassing due to defective lance pressure regulator and extended PM cycle.',
        })

        # Advance D4 -> D5
        capa.action_advance_stage()
        self.assertEqual(capa.state, 'd5_actions')

        # Add Corrective Action lines in D5
        action_line = self.env['qms.capa.action'].create({
            'capa_id': capa.id,
            'name': 'Install digital pressure differential telemetry transducer on nitrogen degassing lance',
            'action_type': 'corrective',
            'assigned_to_id': self.qa_user.id,
            'deadline': fields.Date.today(),
        })
        self.assertEqual(capa.action_count, 1)
        self.assertEqual(capa.action_completed_count, 0)

        # Complete and verify action
        action_line.action_start()
        action_line.action_complete()
        action_line.action_verify()
        self.assertEqual(capa.action_completed_count, 1)

        # Advance D5 -> D6
        capa.action_advance_stage()
        self.assertEqual(capa.state, 'd6_verification')

        # Document Verification evidence & Residual RPN
        capa.write({
            'verification_method': 'zero_defects',
            'verification_result': 'Zero porosity defects detected across 10 consecutive production runs (2,500 units sampled).',
            'verified_by_id': self.qa_user.id,
            'verification_date': fields.Date.today(),
            'residual_severity': 2,
            'residual_occurrence': 2,
            'residual_detection': 2,
        })
        # Residual RPN: 2 * 2 * 2 = 8
        self.assertEqual(capa.residual_rpn, 8)
        self.assertAlmostEqual(capa.rpn_reduction_pct, 96.7, places=1)

        # Advance D6 -> D7 -> D8 (Close)
        capa.action_advance_stage()
        self.assertEqual(capa.state, 'd7_prevention')
        capa.write({
            'preventive_actions': 'Revised Maintenance SOP-MNT-049 to mandate quarterly diaphragm replacement across all 6 casting cells.',
            'sop_updated': True,
            'sop_reference': 'SOP-MNT-049-REV-D',
        })
        capa.action_close_capa()
        self.assertEqual(capa.state, 'd8_closed')
        self.assertTrue(capa.close_date)

    def test_04_iso_audit_and_auto_ncr_trigger(self):
        """Test ISO 9001:2015 audit execution, finding logging, and automatic NCR generation."""
        audit = self.env['qms.audit'].create({
            'title': 'Annual ISO 9001:2015 Operations Audit - Fabrication',
            'audit_type': 'internal',
            'standard': 'iso_9001',
            'lead_auditor_id': self.qa_user.id,
            'audit_date': fields.Date.today(),
        })
        self.assertTrue(audit.name.startswith('AUD/'))

        # Load standard template clauses
        audit.action_load_iso9001_template()
        self.assertEqual(len(audit.line_ids), 11)

        # Mark a major non-conformance on Clause 7.1.5 (Calibration)
        cal_line = audit.line_ids.filtered(lambda l: '7.1.5' in l.clause)
        cal_line.write({
            'result': 'major_nc',
            'evidence': 'Digital Vernier Calipers (SN: CAL-9042) used in final acceptance inspection was 4 months past calibration expiration date.',
        })

        self.assertEqual(audit.major_nc_count, 1)
        self.assertEqual(audit.overall_result, 'failed')

        # Trigger NCR from audit finding
        cal_line.action_generate_ncr()
        self.assertTrue(cal_line.ncr_id)
        self.assertEqual(cal_line.ncr_id.severity, 'critical')
        self.assertEqual(cal_line.ncr_id.source_type, 'audit')

    def test_05_risk_register_fmea(self):
        """Test ISO 9001 Clause 6.1 Quality Risk Register & FMEA scoring."""
        risk = self.env['qms.risk'].create({
            'title': 'Chemical Surface Treatment Tank Temperature Fluctuations',
            'process_step': 'Electroless Nickel Plating Bath',
            'potential_cause': 'Heater coil scaling causing localized thermostat lag',
            'potential_effect': 'Inconsistent plating thickness leading to coating peeling in thermal cycle test',
            'severity': 7,
            'occurrence': 6,
            'detection': 6,
            'responsible_id': self.qa_user.id,
        })
        self.assertTrue(risk.name.startswith('RSK/'))
        # Initial RPN: 7 * 6 * 6 = 252 -> critical
        self.assertEqual(risk.initial_rpn, 252)
        self.assertEqual(risk.risk_level, 'critical')

        # Assess and add mitigation
        risk.action_assess()
        self.assertEqual(risk.state, 'assessed')

        risk.write({
            'mitigation_action': 'Dual-redundant RTD temperature probes with automated PLC cut-off audible alarm',
            'revised_severity': 3,
            'revised_occurrence': 2,
            'revised_detection': 2,
        })
        # Residual RPN: 3 * 2 * 2 = 12
        self.assertEqual(risk.residual_rpn, 12)
        self.assertAlmostEqual(risk.rpn_reduction_pct, 95.2, places=1)

        risk.action_mitigate()
        risk.action_accept()
        self.assertEqual(risk.state, 'accepted')
