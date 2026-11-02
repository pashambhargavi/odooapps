# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.fields import Command


class AccountMove(models.Model):
    _inherit = 'account.move'

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
        'approval.document.step', 'move_id',
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
        for move in self:
            if move.approval_state != 'pending':
                move.is_current_matrix_approver = False
                continue
            pending_steps = move.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and user in s.approver_ids and user not in s.approved_user_ids
            )
            move.is_current_matrix_approver = bool(pending_steps or is_manager)

    def _find_matching_approval_rule(self):
        self.ensure_one()
        if self.move_type not in ('out_invoice', 'in_invoice'):
            return self.env['approval.matrix.rule'].browse()
        return self.env['approval.matrix.rule']._find_matching_rule(
            self.move_type,
            self.company_id,
            abs(self.amount_untaxed),
            abs(self.amount_total),
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
        doc_label = self.name if self.name and self.name != '/' else _('Draft Invoice/Bill #%s') % self.id
        for step in self.approval_step_ids.filtered(lambda s: s.status == 'pending'):
            for approver in step.approver_ids:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=approver.id,
                    summary=_('Invoice/Bill Approval: %s') % doc_label,
                    note=_('%s requires your approval under rule "%s" (%s).') % (
                        doc_label, rule.name, step.tier_name
                    ),
                )
        self.message_post(
            body=_('Document routed for multi-level approval under rule <b>%s</b>.') % rule.name,
        )

    def action_request_approval(self):
        for move in self:
            rule = move._find_matching_approval_rule()
            if not rule:
                raise UserError(_('No active Approval Matrix Rule matches this Invoice/Bill.'))
            move._initiate_approval_matrix(rule)
        return True

    def action_post(self):
        if self.env.context.get('skip_approval_check'):
            return super().action_post()

        moves_to_post = self.browse()
        for move in self:
            if move.move_type not in ('out_invoice', 'in_invoice'):
                moves_to_post |= move
                continue
            if move.approval_state == 'pending':
                raise UserError(_('Document %s is currently waiting for multi-level approval.') % (move.name or move.id))
            if move.approval_state == 'approved':
                moves_to_post |= move
                continue
            rule = move._find_matching_approval_rule()
            if rule:
                move._initiate_approval_matrix(rule)
            else:
                moves_to_post |= move

        if moves_to_post:
            return super(AccountMove, moves_to_post).action_post()
        return False

    def action_approve_matrix(self):
        user = self.env.user
        is_manager = user.has_group('dynamic_approval_governance.group_approval_manager')
        for move in self:
            if move.approval_state != 'pending':
                raise UserError(_('This document is not waiting for approval.'))
            step = move.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and user in s.approver_ids and user not in s.approved_user_ids
            )[:1]
            if not step and is_manager:
                step = move.approval_step_ids.filtered(lambda s: s.status == 'pending')[:1]
            if not step:
                raise UserError(_('You do not have a pending approval tier on this document.'))

            step_sudo = step.sudo()
            move_sudo = move.sudo()
            step_sudo.write({
                'approved_user_ids': [Command.link(user.id)],
                'action_date': fields.Datetime.now(),
            })
            move_sudo.activity_feedback(['mail.mail_activity_data_todo'], user_id=user.id)

            if len(step_sudo.approved_user_ids) >= step_sudo.minimum_approvals or is_manager:
                step_sudo.status = 'approved'
                move_sudo.message_post(
                    body=_('Approval tier <b>%s</b> approved by <b>%s</b>.') % (step_sudo.tier_name, user.name),
                )
                if not move_sudo.approval_step_ids.filtered(lambda s: s.status == 'pending'):
                    waiting_steps = move_sudo.approval_step_ids.filtered(lambda s: s.status == 'waiting').sorted('sequence')
                    if waiting_steps:
                        next_seq = waiting_steps[0].sequence
                        doc_label = move_sudo.name if move_sudo.name and move_sudo.name != '/' else _('Draft Invoice/Bill #%s') % move_sudo.id
                        for next_step in waiting_steps.filtered(lambda s: s.sequence == next_seq):
                            next_step.status = 'pending'
                            for approver in next_step.approver_ids:
                                move_sudo.activity_schedule(
                                    'mail.mail_activity_data_todo',
                                    user_id=approver.id,
                                    summary=_('Invoice/Bill Approval: %s') % doc_label,
                                    note=_('%s requires your approval (%s).') % (doc_label, next_step.tier_name),
                                )

            if all(s.status == 'approved' for s in move_sudo.approval_step_ids):
                move_sudo.approval_state = 'approved'
                move_sudo.message_post(
                    body=_('All approval tiers completed for document <b>%s</b>.') % (move_sudo.name or move_sudo.id),
                )
                if move_sudo.approval_rule_id.auto_confirm_on_approve and move_sudo.state == 'draft':
                    move_sudo.with_context(skip_approval_check=True).action_post()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Invoice / Bill Approval'),
            'res_model': 'approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'account.move',
                'default_res_id': self.id,
            },
        }

    def _apply_rejection(self, reason):
        user = self.env.user
        is_manager = user.has_group('dynamic_approval_governance.group_approval_manager')
        for move in self:
            step = move.approval_step_ids.filtered(
                lambda s: s.status == 'pending' and (user in s.approver_ids or is_manager)
            )[:1]
            if not step:
                raise UserError(_('You are not authorized to reject this Invoice/Bill approval.'))
            move_sudo = move.sudo()
            step.sudo().write({
                'status': 'rejected',
                'action_date': fields.Datetime.now(),
                'note': reason,
            })
            move_sudo.write({
                'approval_state': 'rejected',
                'rejection_reason': reason,
            })
            move_sudo.activity_unlink(['mail.mail_activity_data_todo'])
            move_sudo.message_post(
                body=_('Document approval rejected by <b>%s</b>.<br/><b>Reason:</b> %s') % (user.name, reason),
            )

    def action_reset_approval(self):
        for move in self:
            move.approval_step_ids.unlink()
            move.write({
                'approval_state': 'not_required',
                'approval_rule_id': False,
                'rejection_reason': False,
            })
            move.activity_unlink(['mail.mail_activity_data_todo'])
        return True
