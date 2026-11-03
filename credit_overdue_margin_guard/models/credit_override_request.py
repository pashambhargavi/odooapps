# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class CreditOverrideRequest(models.Model):
    _name = 'credit.override.request'
    _description = 'Customer Credit, Overdue & Margin Override Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Override Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', required=True,
        ondelete='cascade', index=True, tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True,
        index=True, tracking=True,
    )
    policy_id = fields.Many2one(
        'credit.risk.policy', string='Applied Risk Policy',
        tracking=True,
    )
    requested_by_id = fields.Many2one(
        'res.users', string='Requested By',
        default=lambda self: self.env.user, required=True, tracking=True,
    )
    reviewed_by_id = fields.Many2one(
        'res.users', string='Reviewed By', readonly=True, tracking=True,
    )
    reviewed_date = fields.Datetime(
        string='Reviewed On', readonly=True, tracking=True,
    )
    violation_type = fields.Selection([
        ('credit_hold', 'Manual Credit Hold'),
        ('credit_limit', 'Credit Limit Exceeded'),
        ('overdue_aging', 'Overdue Invoice Aging'),
        ('low_margin', 'Below Minimum Margin %'),
        ('multiple', 'Multiple Risk Violations'),
    ], string='Primary Violation Type', required=True, default='credit_limit', tracking=True)

    violation_summary = fields.Char(
        string='Risk Violation Summary', required=True, tracking=True,
    )
    violation_details = fields.Text(
        string='Detailed Risk Breakdown', readonly=True,
    )

    # Snapshot financial & margin metrics at the time of request
    order_amount = fields.Monetary(
        string='Order Total Amount', currency_field='currency_id', readonly=True,
    )
    current_exposure_amount = fields.Monetary(
        string='Existing Receivable Exposure', currency_field='currency_id', readonly=True,
    )
    projected_exposure_amount = fields.Monetary(
        string='Projected Total Exposure', currency_field='currency_id', readonly=True,
    )
    credit_limit_amount = fields.Monetary(
        string='Customer Credit Limit', currency_field='currency_id', readonly=True,
    )
    overdue_invoice_count = fields.Integer(
        string='Overdue Invoices Count', readonly=True,
    )
    oldest_overdue_days = fields.Integer(
        string='Oldest Overdue (Days)', readonly=True,
    )
    order_margin_percent = fields.Float(
        string='Order Margin (%)', readonly=True,
    )
    min_margin_percent = fields.Float(
        string='Required Minimum Margin (%)', readonly=True,
    )

    justification = fields.Text(
        string='Salesperson Justification / Notes',
        tracking=True,
    )
    rejection_reason = fields.Text(
        string='Finance Rejection Reason', readonly=True, tracking=True,
    )
    state = fields.Selection([
        ('pending', 'Pending Finance Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='pending', required=True, tracking=True, index=True)

    can_current_user_review = fields.Boolean(
        string='Can Current User Review',
        compute='_compute_can_current_user_review',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('credit.override.request') or _('New')
        return super().create(vals_list)

    def _compute_can_current_user_review(self):
        user = self.env.user
        is_manager = user.has_group('credit_overdue_margin_guard.group_credit_guard_manager')
        for rec in self:
            if rec.state != 'pending':
                rec.can_current_user_review = False
            elif is_manager:
                rec.can_current_user_review = True
            elif rec.policy_id and user in rec.policy_id.approver_ids:
                rec.can_current_user_review = True
            else:
                rec.can_current_user_review = False

    def _check_reviewer_permission(self):
        self.ensure_one()
        user = self.env.user
        is_manager = user.has_group('credit_overdue_margin_guard.group_credit_guard_manager')
        is_policy_approver = bool(self.policy_id and user in self.policy_id.approver_ids)
        if not (is_manager or is_policy_approver):
            raise AccessError(_(
                'Only Credit & Margin Controllers or assigned Policy Approvers can approve or reject override requests.'
            ))

    def action_approve(self):
        for rec in self:
            if rec.state != 'pending':
                raise UserError(_('Only pending override requests can be approved.'))
            rec._check_reviewer_permission()
            rec.sudo().write({
                'state': 'approved',
                'reviewed_by_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
            })
            order = rec.sale_order_id.sudo()
            if order.exists():
                order.write({
                    'risk_hold_state': 'overridden',
                    'risk_violation_summary': _(
                        'Approved via Override %s by %s'
                    ) % (rec.name, self.env.user.name),
                })
                order.message_post(
                    body=_(
                        'Credit & Margin Override <b>%s</b> approved by <b>%s</b>.'
                    ) % (rec.name, self.env.user.name),
                    subtype_xmlid='mail.mt_note',
                )
                auto_confirm = rec.policy_id.auto_confirm_on_override if rec.policy_id else True
                if auto_confirm and order.state in ('draft', 'sent'):
                    order.with_context(skip_credit_margin_check=True).action_confirm()
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        if self.state != 'pending':
            raise UserError(_('Only pending override requests can be rejected.'))
        self._check_reviewer_permission()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Credit / Margin Override'),
            'res_model': 'credit.override.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_override_request_id': self.id},
        }

    def _apply_rejection(self, reason):
        for rec in self:
            rec._check_reviewer_permission()
            rec.sudo().write({
                'state': 'rejected',
                'reviewed_by_id': self.env.user.id,
                'reviewed_date': fields.Datetime.now(),
                'rejection_reason': reason,
            })
            order = rec.sale_order_id.sudo()
            if order.exists():
                order.write({
                    'risk_hold_state': 'rejected',
                    'risk_violation_summary': _(
                        'Override %s Rejected by %s: %s'
                    ) % (rec.name, self.env.user.name, reason),
                })
                order.message_post(
                    body=_(
                        'Credit & Margin Override <b>%s</b> rejected by <b>%s</b>.<br/>'
                        '<b>Reason:</b> %s'
                    ) % (rec.name, self.env.user.name, reason),
                    subtype_xmlid='mail.mt_note',
                )

    def action_cancel(self):
        for rec in self:
            if rec.state not in ('pending', 'rejected'):
                raise UserError(_('Only pending or rejected requests can be cancelled.'))
            rec.write({'state': 'cancel'})

    def action_reset_to_pending(self):
        for rec in self:
            if rec.state not in ('rejected', 'cancel'):
                raise UserError(_('Only rejected or cancelled requests can be reset to pending.'))
            rec.write({
                'state': 'pending',
                'reviewed_by_id': False,
                'reviewed_date': False,
                'rejection_reason': False,
            })
            if rec.sale_order_id.exists():
                rec.sale_order_id.sudo().write({'risk_hold_state': 'on_hold'})

    def action_view_sale_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
