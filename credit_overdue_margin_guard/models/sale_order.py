# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    purchase_price = fields.Float(
        string='Unit Cost',
        digits='Product Price',
        compute='_compute_purchase_price',
        store=True,
        readonly=False,
    )
    margin_amount = fields.Monetary(
        string='Margin Amount',
        currency_field='currency_id',
        compute='_compute_margin_metrics',
        store=True,
    )
    margin_percent = fields.Float(
        string='Margin (%)',
        compute='_compute_margin_metrics',
        store=True,
    )

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom_id')
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id or line.display_type:
                line.purchase_price = 0.0
                continue
            product_cost = line.product_id.with_company(line.company_id).standard_price
            if line.product_uom_id and line.product_uom_id != line.product_id.uom_id:
                product_cost = line.product_id.uom_id._compute_price(
                    product_cost, line.product_uom_id
                )
            if line.currency_id and line.company_id.currency_id and line.currency_id != line.company_id.currency_id:
                product_cost = line.company_id.currency_id._convert(
                    product_cost,
                    line.currency_id,
                    line.company_id,
                    line.order_id.date_order or fields.Date.context_today(line),
                )
            line.purchase_price = product_cost

    @api.depends('price_subtotal', 'product_uom_qty', 'purchase_price')
    def _compute_margin_metrics(self):
        for line in self:
            if line.display_type:
                line.margin_amount = 0.0
                line.margin_percent = 0.0
                continue
            total_cost = line.purchase_price * line.product_uom_qty
            margin = line.price_subtotal - total_cost
            line.margin_amount = margin
            line.margin_percent = (margin / line.price_subtotal * 100.0) if line.price_subtotal else 0.0


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    total_cost_amount = fields.Monetary(
        string='Total Cost',
        currency_field='currency_id',
        compute='_compute_order_margin_totals',
        store=True,
    )
    order_margin_amount = fields.Monetary(
        string='Total Order Margin',
        currency_field='currency_id',
        compute='_compute_order_margin_totals',
        store=True,
    )
    order_margin_percent = fields.Float(
        string='Order Margin (%)',
        compute='_compute_order_margin_totals',
        store=True,
    )

    risk_hold_state = fields.Selection([
        ('clear', 'Clear (No Violations)'),
        ('warning', 'Soft Risk Warning'),
        ('on_hold', 'On Credit / Margin Hold'),
        ('overridden', 'Approved via Override'),
        ('rejected', 'Override Rejected'),
    ], string='Risk Control Status', default='clear', copy=False, tracking=True)

    risk_violation_summary = fields.Text(
        string='Risk Evaluation Details', readonly=True, copy=False,
    )

    credit_override_ids = fields.One2many(
        'credit.override.request', 'sale_order_id',
        string='Credit & Margin Overrides', copy=False,
    )
    credit_override_count = fields.Integer(
        string='Overrides Count',
        compute='_compute_credit_override_info',
    )
    pending_override_id = fields.Many2one(
        'credit.override.request',
        string='Pending Override Request',
        compute='_compute_credit_override_info',
    )
    can_approve_credit_override = fields.Boolean(
        string='Can Approve Credit Override',
        compute='_compute_credit_override_info',
    )

    # Related partner risk snapshot fields for quick visibility on the Sales Order form
    partner_credit_limit = fields.Monetary(
        related='partner_id.effective_credit_limit',
        string='Customer Credit Limit', readonly=True,
    )
    partner_total_exposure = fields.Monetary(
        related='partner_id.total_receivable_exposure',
        string='Current Receivable Exposure', readonly=True,
    )
    partner_available_credit = fields.Monetary(
        related='partner_id.available_credit_balance',
        string='Available Credit Balance', readonly=True,
    )
    partner_oldest_overdue_days = fields.Integer(
        related='partner_id.oldest_overdue_days',
        string='Customer Oldest Overdue (Days)', readonly=True,
    )

    @api.depends('order_line.margin_amount', 'order_line.purchase_price', 'order_line.product_uom_qty', 'amount_untaxed')
    def _compute_order_margin_totals(self):
        for order in self:
            valid_lines = order.order_line.filtered(lambda l: not l.display_type)
            total_cost = sum(l.purchase_price * l.product_uom_qty for l in valid_lines)
            margin_amt = order.amount_untaxed - total_cost
            order.total_cost_amount = total_cost
            order.order_margin_amount = margin_amt
            order.order_margin_percent = (margin_amt / order.amount_untaxed * 100.0) if order.amount_untaxed else 0.0

    def _compute_credit_override_info(self):
        for order in self:
            order.credit_override_count = len(order.credit_override_ids)
            pending = order.credit_override_ids.filtered(lambda r: r.state == 'pending')[:1]
            order.pending_override_id = pending
            order.can_approve_credit_override = bool(pending and pending.can_current_user_review)

    def _evaluate_credit_overdue_margin_risk(self):
        """Evaluate the 4-point commercial risk rules for this Sales Order.

        Returns a dict:
            {
                'enforcement_mode': 'allow' | 'warning' | 'block',
                'policy': credit.risk.policy record,
                'violations': list of (code, title, detail),
            }
        """
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id or self.partner_id
        policy = partner.credit_policy_id or self.env['credit.risk.policy'].search(
            [('company_id', '=', self.company_id.id)], order='sequence, id', limit=1
        )

        if partner.credit_enforcement_mode != 'policy':
            enforcement_mode = partner.credit_enforcement_mode
        elif policy:
            enforcement_mode = policy.enforcement_mode
        else:
            enforcement_mode = 'allow'

        violations = []

        # Rule 1: Manual Credit Hold on Customer
        if partner.is_credit_hold:
            reason_suffix = f" ({partner.credit_hold_reason})" if partner.credit_hold_reason else ""
            violations.append((
                'credit_hold',
                _('Customer Account on Manual Credit Hold'),
                _('Customer %s is placed on Manual Credit Hold%s.') % (partner.name, reason_suffix),
            ))

        # Rule 2: Total Credit Exposure Limit
        credit_limit = partner.effective_credit_limit
        current_exposure = partner.total_receivable_exposure
        projected_exposure = current_exposure + self.amount_total
        if credit_limit > 0 and projected_exposure > credit_limit:
            violations.append((
                'credit_limit',
                _('Credit Limit Exceeded'),
                _(
                    'Projected exposure (%.2f) exceeds customer credit limit (%.2f). '
                    '[Current Exposure: %.2f + Order Total: %.2f]'
                ) % (projected_exposure, credit_limit, current_exposure, self.amount_total),
            ))

        # Rule 3: Overdue Invoice Aging Gate
        if policy and policy.check_overdue_aging:
            if partner.oldest_overdue_days > policy.max_overdue_days:
                violations.append((
                    'overdue_aging',
                    _('Overdue Invoice Aging Exceeded'),
                    _(
                        'Customer has unpaid invoices overdue by %s days (Max allowed: %s days).'
                    ) % (partner.oldest_overdue_days, policy.max_overdue_days),
                ))
            elif policy.max_overdue_invoices > 0 and partner.overdue_invoice_count > policy.max_overdue_invoices:
                violations.append((
                    'overdue_aging',
                    _('Max Overdue Invoices Count Exceeded'),
                    _(
                        'Customer has %s overdue unpaid invoices (Max allowed: %s invoices).'
                    ) % (partner.overdue_invoice_count, policy.max_overdue_invoices),
                ))

        # Rule 4: Minimum Profit Margin % Guard
        if policy and policy.check_minimum_margin and self.amount_untaxed > 0:
            if self.order_margin_percent < policy.min_margin_percent:
                violations.append((
                    'low_margin',
                    _('Below Minimum Profit Margin %'),
                    _(
                        'Order Margin is %.2f%%, which is below the required minimum margin of %.2f%%.'
                    ) % (self.order_margin_percent, policy.min_margin_percent),
                ))

        return {
            'enforcement_mode': enforcement_mode,
            'policy': policy,
            'violations': violations,
        }

    def action_confirm(self):
        if self.env.context.get('skip_credit_margin_check'):
            return super().action_confirm()

        orders_to_confirm = self.env['sale.order']
        for order in self:
            if order.risk_hold_state == 'overridden':
                orders_to_confirm |= order
                continue

            eval_res = order._evaluate_credit_overdue_margin_risk()
            violations = eval_res['violations']
            mode = eval_res['enforcement_mode']
            policy = eval_res['policy']
            partner = order.partner_id.commercial_partner_id or order.partner_id

            # Manual Credit Hold always blocks unless overridden or mode is explicitly allow
            effective_block = (mode == 'block') or (partner.is_credit_hold and mode != 'allow')

            if not violations or mode == 'allow':
                order.risk_hold_state = 'clear'
                order.risk_violation_summary = False
                orders_to_confirm |= order
                continue

            summary_titles = ', '.join(v[1] for v in violations)
            detail_lines = '\n'.join(f"• {v[1]}: {v[2]}" for v in violations)

            if not effective_block and mode == 'warning':
                order.risk_hold_state = 'warning'
                order.risk_violation_summary = detail_lines
                order.message_post(
                    body=_(
                        '<b>Soft Credit / Margin Risk Warning on Confirmation:</b><br/>%s'
                    ) % '<br/>'.join(f"• {v[1]}: {v[2]}" for v in violations),
                    subtype_xmlid='mail.mt_note',
                )
                orders_to_confirm |= order
            else:
                # Place order on hold and create/update a pending Credit Override Request
                primary_code = violations[0][0] if len(violations) == 1 else 'multiple'
                order.risk_hold_state = 'on_hold'
                order.risk_violation_summary = detail_lines

                existing_pending = order.credit_override_ids.filtered(lambda r: r.state == 'pending')[:1]
                override_vals = {
                    'sale_order_id': order.id,
                    'partner_id': partner.id,
                    'policy_id': policy.id if policy else False,
                    'requested_by_id': self.env.user.id,
                    'violation_type': primary_code,
                    'violation_summary': summary_titles,
                    'violation_details': detail_lines,
                    'order_amount': order.amount_total,
                    'current_exposure_amount': partner.total_receivable_exposure,
                    'projected_exposure_amount': partner.total_receivable_exposure + order.amount_total,
                    'credit_limit_amount': partner.effective_credit_limit,
                    'overdue_invoice_count': partner.overdue_invoice_count,
                    'oldest_overdue_days': partner.oldest_overdue_days,
                    'order_margin_percent': order.order_margin_percent,
                    'min_margin_percent': policy.min_margin_percent if policy else 0.0,
                }
                if existing_pending:
                    existing_pending.sudo().write(override_vals)
                    override_req = existing_pending
                else:
                    override_req = self.env['credit.override.request'].sudo().create(override_vals)

                order.message_post(
                    body=_(
                        '<b>Sales Order Placed on Credit / Margin Hold</b><br/>'
                        'Override Request <b>%s</b> has been generated for Finance review:<br/>%s'
                    ) % (
                        override_req.name,
                        '<br/>'.join(f"• {v[1]}: {v[2]}" for v in violations),
                    ),
                    subtype_xmlid='mail.mt_note',
                )

        if orders_to_confirm:
            return super(SaleOrder, orders_to_confirm).action_confirm()
        return True

    def action_approve_credit_override(self):
        self.ensure_one()
        if not self.pending_override_id:
            raise UserError(_('There is no pending Credit / Margin Override Request for this order.'))
        return self.pending_override_id.action_approve()

    def action_open_credit_reject_wizard(self):
        self.ensure_one()
        if not self.pending_override_id:
            raise UserError(_('There is no pending Credit / Margin Override Request for this order.'))
        return self.pending_override_id.action_open_reject_wizard()

    def action_view_credit_overrides(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit & Margin Overrides - %s') % self.name,
            'res_model': 'credit.override.request',
            'view_mode': 'list,kanban,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }
