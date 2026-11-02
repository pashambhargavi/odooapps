# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged
from odoo.fields import Command


@tagged('post_install', '-at_install')
class TestApprovalGovernance(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_tier1 = cls.env['res.users'].create({
            'name': 'Tier 1 Approver',
            'login': 'tier1_approver@example.com',
            'email': 'tier1_approver@example.com',
            'group_ids': [Command.link(cls.env.ref('base.group_user').id)],
        })
        cls.user_tier2 = cls.env['res.users'].create({
            'name': 'Tier 2 Approver',
            'login': 'tier2_approver@example.com',
            'email': 'tier2_approver@example.com',
            'group_ids': [Command.link(cls.env.ref('base.group_user').id)],
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Enterprise Client Corp',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Server Rack Hardware',
            'list_price': 1000.0,
            'standard_price': 700.0,
        })

    def test_01_standalone_sequential_approval_request(self):
        category = self.env['approval.category'].create({
            'name': 'IT CapEx Approval',
            'approval_minimum': 2,
            'enforce_sequential': True,
            'has_amount': 'required',
            'approver_ids': [
                Command.create({
                    'sequence': 10,
                    'user_id': self.user_tier1.id,
                    'role_title': 'IT Manager',
                    'required': True,
                }),
                Command.create({
                    'sequence': 20,
                    'user_id': self.user_tier2.id,
                    'role_title': 'CFO',
                    'required': True,
                }),
            ],
        })
        request = self.env['approval.request'].create({
            'name': 'Purchase 5 Server Racks',
            'category_id': category.id,
            'amount': 5000.0,
        })
        self.assertEqual(request.request_status, 'new')
        self.assertEqual(len(request.approver_ids), 2)

        request.action_confirm()
        self.assertEqual(request.request_status, 'pending')
        step1, step2 = request.approver_ids.sorted('sequence')
        self.assertEqual(step1.status, 'pending')
        self.assertEqual(step2.status, 'waiting')

        # Tier 1 approves -> Tier 2 becomes pending
        request.with_user(self.user_tier1).action_approve()
        self.assertEqual(step1.status, 'approved')
        self.assertEqual(step2.status, 'pending')
        self.assertEqual(request.request_status, 'pending')

        # Tier 2 approves -> Request becomes approved
        request.with_user(self.user_tier2).action_approve()
        self.assertEqual(step2.status, 'approved')
        self.assertEqual(request.request_status, 'approved')
        self.assertTrue(request.date_approved)

    def test_02_sale_order_matrix_approval_and_rejection(self):
        rule = self.env['approval.matrix.rule'].create({
            'name': 'SO Governance > 2000 or Discount > 10%',
            'target_model': 'sale_order',
            'amount_basis': 'amount_total',
            'min_amount': 2000.0,
            'check_discount_limit': True,
            'max_discount_percent': 10.0,
            'enforce_sequential': True,
            'auto_confirm_on_approve': True,
            'line_ids': [
                Command.create({
                    'sequence': 10,
                    'tier_name': 'Tier 1 - Sales Lead',
                    'approver_ids': [Command.set([self.user_tier1.id])],
                    'minimum_approvals': 1,
                }),
                Command.create({
                    'sequence': 20,
                    'tier_name': 'Tier 2 - Finance Director',
                    'approver_ids': [Command.set([self.user_tier2.id])],
                    'minimum_approvals': 1,
                }),
            ],
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'product_uom_qty': 3,
                    'price_unit': 1000.0,
                }),
            ],
        })
        # Attempting to confirm triggers multi-level approval instead of confirming immediately
        order.action_confirm()
        self.assertEqual(order.state, 'draft')
        self.assertEqual(order.approval_state, 'pending')
        self.assertEqual(order.approval_rule_id, rule)
        self.assertEqual(len(order.approval_step_ids), 2)

        # Reject via wizard
        wizard = self.env['approval.reject.wizard'].with_user(self.user_tier1).create({
            'res_model': 'sale.order',
            'res_id': order.id,
            'reason': 'Margin too low for Q4 policy',
        })
        wizard.action_confirm_reject()
        self.assertEqual(order.approval_state, 'rejected')
        self.assertEqual(order.rejection_reason, 'Margin too low for Q4 policy')

        # Reset and approve through both tiers -> auto-confirms SO
        order.action_reset_approval()
        order.action_confirm()
        self.assertEqual(order.approval_state, 'pending')

        order.with_user(self.user_tier1).action_approve_matrix()
        self.assertEqual(order.approval_state, 'pending')
        self.assertEqual(order.state, 'draft')

        order.approval_step_ids.sorted('sequence')[1].approver_ids = [Command.link(self.env.user.id)]
        order.action_approve_matrix()
        self.assertEqual(order.approval_state, 'approved')
        self.assertEqual(order.state, 'sale')
