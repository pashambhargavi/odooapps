# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    approval_rule_id = fields.Many2one(
        'approval.matrix.rule', string='Approval Matrix Rule',
        copy=False, readonly=True, tracking=True,
    )
    approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Waiting for Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Approval Status', default='not_required', copy=False, tracking=True)
    approval_step_ids = fields.One2many(
        'approval.document.step', 'purchase_order_id',
        string='Approval Tiers', copy=False,
    )
    is_current_matrix_approver = fields.Boolean(
        string='Is Current Matrix Approver',
        compute='_compute_is_current_matrix_approver',
    )
    rejection_reason = fields.Text(
        string='Rejection Reason', copy=False, readonly=True, tracking=True,
    )

    @api.depends('approval_state', 'approval_step_ids.status', 'approval_step_ids.approver_ids', 'approval_step_ids.approved_user_ids')
    def _compute_is_current_matrix_approver(self):
        user = self.env.user
        is_manager = user.has_group('dynamic_approval_governance.group_approval_manager')
        for order in self:
            if order.approval_state != 'pending':
                order.is_current_matrix_approver = False
                continue
            pending_steps = order.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and user in s.approver_ids and user not in s.approved_user_ids
            )
            order.is_current_matrix_approver = bool(pending_steps or is_manager)

    def _find_matching_approval_rule(self):
        self.ensure_one()
        return self.env['approval.matrix.rule']._find_matching_rule(
            'purchase_order',
            self.company_id,
            self.amount_untaxed,
            self.amount_total,
        )

    def _initiate_approval_matrix(self, rule):
        self.ensure_one()
        commands = [Command.clear()]
        sorted_lines = rule.line_ids.sorted('sequence')
        first_seq = sorted_lines[0].sequence if sorted_lines else False
        for line in sorted_lines:
            status = 'pending' if (not rule.enforce_sequential or line.sequence == first_seq) else 'waiting'
            commands.append(Command.create({
                'sequence': line.sequence,
                'tier_name': line.tier_name,
                'rule_id': rule.id,
                'approver_ids': [Command.set(line.approver_ids.ids)],
                'minimum_approvals': line.minimum_approvals,
                'status': status,
            }))
        self.write({
            'approval_rule_id': rule.id,
            'approval_state': 'pending',
            'approval_step_ids': commands,
            'rejection_reason': False,
        })
        for step in self.approval_step_ids.filtered(lambda s: s.status == 'pending'):
            for approver in step.approver_ids:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=approver.id,
                    summary=_('Purchase Order Approval: %s') % self.name,
                    note=_('Purchase Order %s requires your approval under rule "%s" (%s).') % (
                        self.name, rule.name, step.tier_name
                    ),
                )
        self.message_post(
            body=_('Purchase Order routed for multi-level approval under rule <b>%s</b>.') % rule.name,
        )

    def action_request_approval(self):
        for order in self:
            rule = order._find_matching_approval_rule()
            if not rule:
                raise UserError(_('No active Approval Matrix Rule matches this Purchase Order.'))
            order._initiate_approval_matrix(rule)
        return True

    def button_confirm(self):
        if self.env.context.get('skip_approval_check'):
            return super().button_confirm()

        orders_to_confirm = self.browse()
        for order in self:
            if order.approval_state == 'pending':
                raise UserError(_('Purchase Order %s is currently waiting for multi-level approval.') % order.name)
            if order.approval_state == 'approved':
                orders_to_confirm |= order
                continue
            rule = order._find_matching_approval_rule()
            if rule:
                order._initiate_approval_matrix(rule)
            else:
                orders_to_confirm |= order

        if orders_to_confirm:
            return super(PurchaseOrder, orders_to_confirm).button_confirm()
        return True

    def action_approve_matrix(self):
        user = self.env.user
        is_manager = user.has_group('dynamic_approval_governance.group_approval_manager')
        for order in self:
            if order.approval_state != 'pending':
                raise UserError(_('This Purchase Order is not waiting for approval.'))
            step = order.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and user in s.approver_ids and user not in s.approved_user_ids
            )[:1]
            if not step and is_manager:
                step = order.approval_step_ids.filtered(lambda s: s.status == 'pending')[:1]
            if not step:
                raise UserError(_('You do not have a pending approval tier on this Purchase Order.'))

            step_sudo = step.sudo()
            order_sudo = order.sudo()
            step_sudo.write({
                'approved_user_ids': [Command.link(user.id)],
                'action_date': fields.Datetime.now(),
            })
            order_sudo.activity_feedback(['mail.mail_activity_data_todo'], user_id=user.id)

            if len(step_sudo.approved_user_ids) >= step_sudo.minimum_approvals or is_manager:
                step_sudo.status = 'approved'
                order_sudo.message_post(
                    body=_('Approval tier <b>%s</b> approved by <b>%s</b>.') % (step_sudo.tier_name, user.name),
                )
                if not order_sudo.approval_step_ids.filtered(lambda s: s.status == 'pending'):
                    waiting_steps = order_sudo.approval_step_ids.filtered(lambda s: s.status == 'waiting').sorted('sequence')
                    if waiting_steps:
                        next_seq = waiting_steps[0].sequence
                        for next_step in waiting_steps.filtered(lambda s: s.sequence == next_seq):
                            next_step.status = 'pending'
                            for approver in next_step.approver_ids:
                                order_sudo.activity_schedule(
                                    'mail.mail_activity_data_todo',
                                    user_id=approver.id,
                                    summary=_('Purchase Order Approval: %s') % order_sudo.name,
                                    note=_('Purchase Order %s requires your approval (%s).') % (order_sudo.name, next_step.tier_name),
                                )

            if all(s.status == 'approved' for s in order_sudo.approval_step_ids):
                order_sudo.approval_state = 'approved'
                order_sudo.message_post(
                    body=_('All approval tiers completed for Purchase Order <b>%s</b>.') % order_sudo.name,
                )
                if order_sudo.approval_rule_id.auto_confirm_on_approve and order_sudo.state in ('draft', 'sent'):
                    order_sudo.with_context(skip_approval_check=True).button_confirm()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Purchase Order Approval'),
            'res_model': 'approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'purchase.order',
                'default_res_id': self.id,
            },
        }

    def _apply_rejection(self, reason):
        user = self.env.user
        is_manager = user.has_group('dynamic_approval_governance.group_approval_manager')
        for order in self:
            step = order.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and (user in s.approver_ids or is_manager)
            )[:1]
            if not step:
                raise UserError(_('You are not authorized to reject this Purchase Order approval.'))
            order_sudo = order.sudo()
            step.sudo().write({
                'status': 'rejected',
                'action_date': fields.Datetime.now(),
                'note': reason,
            })
            order_sudo.write({
                'approval_state': 'rejected',
                'rejection_reason': reason,
            })
            order_sudo.activity_unlink(['mail.mail_activity_data_todo'])
            order_sudo.message_post(
                body=_('Purchase Order approval rejected by <b>%s</b>.<br/><b>Reason:</b> %s') % (user.name, reason),
            )

    def action_reset_approval(self):
        for order in self:
            order.approval_step_ids.unlink()
            order.write({
                'approval_state': 'not_required',
                'approval_rule_id': False,
                'rejection_reason': False,
            })
            order.activity_unlink(['mail.mail_activity_data_todo'])
        return True
