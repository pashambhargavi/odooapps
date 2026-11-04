# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestRmaWorkflow(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env['res.partner'].create({
            'name': 'Premier Industrial Client Corp',
            'email': 'client@premier.com',
            'phone': '+1 (555) 777-8899',
        })
        cls.product_a = cls.env['product.product'].create({
            'name': 'Precision Hydraulic Pump',
            'type': 'consu',
            'list_price': 1500.0,
            'standard_price': 800.0,
        })
        cls.reason_defect = cls.env['rma.reason'].create({
            'name': 'Defective on Arrival',
            'code': 'DEFECT',
            'default_action': 'refund',
        })
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)

    def _create_rma(self, **kwargs):
        vals = {
            'partner_id': self.customer.id,
            'warehouse_id': self.warehouse.id,
            'line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'ordered_qty': 5.0,
                'delivered_qty': 5.0,
                'return_qty': 2.0,
                'unit_price': 1500.0,
                'reason_id': self.reason_defect.id,
                'action_type': 'refund',
            })],
        }
        vals.update(kwargs)
        return self.env['rma.order'].create(vals)

    def test_01_rma_totals_and_approve(self):
        rma = self._create_rma()
        self.assertEqual(rma.state, 'draft')
        self.assertAlmostEqual(rma.total_returned_qty, 2.0)
        self.assertAlmostEqual(rma.total_refund_amount, 3000.0)

        rma.action_approve()
        self.assertEqual(rma.state, 'approved')

    def test_02_rma_receive_goods_creates_picking(self):
        rma = self._create_rma()
        rma.action_approve()
        rma.action_receive_goods()

        self.assertEqual(rma.state, 'received')
        self.assertTrue(rma.return_picking_id)
        self.assertEqual(rma.return_picking_id.picking_type_id.code, 'incoming')
        self.assertEqual(rma.return_picking_count, 1)

    def test_03_quality_inspection_wizard_and_refund(self):
        rma = self._create_rma()
        rma.action_approve()
        rma.action_receive_goods()

        wizard = self.env['rma.inspection.wizard'].with_context(active_id=rma.id).create({
            'rma_id': rma.id,
            'global_disposition': 'refund',
            'internal_notes': 'Shaft seal cracked, verified manufacturer fault.',
        })
        wizard.action_apply_inspection()

        self.assertEqual(rma.state, 'inspected')
        self.assertTrue(rma.credit_note_id)
        self.assertEqual(rma.credit_note_id.move_type, 'out_refund')
        self.assertAlmostEqual(rma.credit_note_id.amount_untaxed, 3000.0)

    def test_04_replacement_delivery_action(self):
        rma = self._create_rma(resolution_type='replacement')
        rma.action_approve()
        rma.action_receive_goods()

        wizard = self.env['rma.inspection.wizard'].with_context(active_id=rma.id).create({
            'rma_id': rma.id,
            'global_disposition': 'replacement',
        })
        wizard.action_apply_inspection()

        self.assertTrue(rma.replacement_picking_id)
        self.assertEqual(rma.replacement_picking_id.picking_type_id.code, 'outgoing')
        self.assertEqual(rma.replacement_picking_count, 1)

    def test_05_guards(self):
        rma = self.env['rma.order'].create({'partner_id': self.customer.id})
        with self.assertRaises(UserError):
            rma.action_approve()
