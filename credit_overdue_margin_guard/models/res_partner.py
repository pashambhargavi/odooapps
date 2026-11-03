# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _default_credit_policy_id(self):
        return self.env['credit.risk.policy'].search([], order='sequence, id', limit=1)

    credit_policy_id = fields.Many2one(
        'credit.risk.policy', string='Credit & Margin Policy',
        default=_default_credit_policy_id, tracking=True,
    )
    credit_enforcement_mode = fields.Selection([
        ('policy', 'Use Policy Default'),
        ('allow', 'No Block (Monitor Only)'),
        ('warning', 'Soft Warning Banner Only'),
        ('block', 'Strict Block (Require Override)'),
    ], string='Credit Enforcement', default='policy', required=True, tracking=True)

    custom_credit_limit = fields.Monetary(
        string='Custom Credit Limit',
        currency_field='currency_id', default=0.0, tracking=True,
        help='If greater than 0, overrides the Default Credit Limit from the assigned Credit Policy.',
    )
    effective_credit_limit = fields.Monetary(
        string='Effective Credit Limit',
        currency_field='currency_id',
        compute='_compute_effective_thresholds',
    )
    effective_max_overdue_days = fields.Integer(
        string='Max Overdue Days',
        compute='_compute_effective_thresholds',
    )
    effective_min_margin_percent = fields.Float(
        string='Min Required Margin (%)',
        compute='_compute_effective_thresholds',
    )

    is_credit_hold = fields.Boolean(
        string='Manual Credit Hold', default=False, tracking=True,
        help='When enabled, all new Sales Orders for this customer are blocked until Finance approves an override.',
    )
    credit_hold_reason = fields.Char(
        string='Credit Hold Reason', tracking=True,
    )

    # Computed Live Exposure & Aging Metrics
    unpaid_invoice_amount = fields.Monetary(
        string='Unpaid Invoices Balance',
        currency_field='currency_id',
        compute='_compute_credit_exposure_metrics',
    )
    uninvoiced_sale_amount = fields.Monetary(
        string='Uninvoiced Sales Orders',
        currency_field='currency_id',
        compute='_compute_credit_exposure_metrics',
    )
    total_receivable_exposure = fields.Monetary(
        string='Total Credit Exposure',
        currency_field='currency_id',
        compute='_compute_credit_exposure_metrics',
    )
    available_credit_balance = fields.Monetary(
        string='Available Credit',
        currency_field='currency_id',
        compute='_compute_credit_exposure_metrics',
    )
    overdue_invoice_count = fields.Integer(
        string='Overdue Invoices Count',
        compute='_compute_credit_exposure_metrics',
    )
    overdue_invoice_amount = fields.Monetary(
        string='Overdue Amount',
        currency_field='currency_id',
        compute='_compute_credit_exposure_metrics',
    )
    oldest_overdue_days = fields.Integer(
        string='Oldest Overdue (Days)',
        compute='_compute_credit_exposure_metrics',
    )
    credit_risk_status = fields.Selection([
        ('healthy', 'Healthy'),
        ('near_limit', 'Near Credit Limit (>80%)'),
        ('over_limit', 'Over Limit / Overdue'),
        ('on_hold', 'On Manual Credit Hold'),
    ], string='Credit Risk Status', compute='_compute_credit_exposure_metrics')

    credit_override_count = fields.Integer(
        string='Credit Overrides Count',
        compute='_compute_credit_override_count',
    )

    @api.depends('credit_policy_id', 'custom_credit_limit')
    def _compute_effective_thresholds(self):
        for partner in self:
            policy = partner.credit_policy_id
            partner.effective_credit_limit = (
                partner.custom_credit_limit
                if partner.custom_credit_limit > 0
                else (policy.default_credit_limit if policy else 0.0)
            )
            partner.effective_max_overdue_days = policy.max_overdue_days if policy else 30
            partner.effective_min_margin_percent = policy.min_margin_percent if policy else 0.0

    def _compute_credit_exposure_metrics(self):
        today = fields.Date.context_today(self)
        for partner in self:
            commercial = partner.commercial_partner_id or partner
            if not commercial.id:
                partner.unpaid_invoice_amount = 0.0
                partner.uninvoiced_sale_amount = 0.0
                partner.total_receivable_exposure = 0.0
                partner.available_credit_balance = partner.effective_credit_limit
                partner.overdue_invoice_count = 0
                partner.overdue_invoice_amount = 0.0
                partner.oldest_overdue_days = 0
                partner.credit_risk_status = 'on_hold' if partner.is_credit_hold else 'healthy'
                continue

            # 1. Unpaid posted customer invoices
            invoices = self.env['account.move'].search([
                ('partner_id', 'child_of', commercial.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
            ])
            unpaid_total = sum(invoices.mapped('amount_residual'))
            overdue_invs = invoices.filtered(lambda m: m.invoice_date_due and m.invoice_date_due < today)
            overdue_total = sum(overdue_invs.mapped('amount_residual'))
            oldest_days = 0
            if overdue_invs:
                oldest_due = min(overdue_invs.mapped('invoice_date_due'))
                oldest_days = max((today - oldest_due).days, 0)

            # 2. Confirmed Sales Orders not yet fully invoiced
            confirmed_orders = self.env['sale.order'].search([
                ('partner_id', 'child_of', commercial.id),
                ('state', '=', 'sale'),
                ('invoice_status', '!=', 'invoiced'),
            ])
            uninvoiced_so = sum(confirmed_orders.mapped('amount_total'))

            exposure = unpaid_total + uninvoiced_so
            limit = partner.effective_credit_limit
            available = limit - exposure if limit > 0 else 0.0

            partner.unpaid_invoice_amount = unpaid_total
            partner.uninvoiced_sale_amount = uninvoiced_so
            partner.total_receivable_exposure = exposure
            partner.available_credit_balance = available
            partner.overdue_invoice_count = len(overdue_invs)
            partner.overdue_invoice_amount = overdue_total
            partner.oldest_overdue_days = oldest_days

            if partner.is_credit_hold:
                partner.credit_risk_status = 'on_hold'
            elif (limit > 0 and exposure > limit) or (
                partner.credit_policy_id.check_overdue_aging
                and oldest_days > partner.effective_max_overdue_days
            ):
                partner.credit_risk_status = 'over_limit'
            elif limit > 0 and exposure >= (limit * 0.8):
                partner.credit_risk_status = 'near_limit'
            else:
                partner.credit_risk_status = 'healthy'

    def _compute_credit_override_count(self):
        data = self.env['credit.override.request']._read_group(
            [('partner_id', 'child_of', self.ids)],
            ['partner_id'],
            ['__count'],
        )
        counts = {partner.id: count for partner, count in data}
        for partner in self:
            partner.credit_override_count = counts.get(partner.id, 0)

    def action_view_credit_overrides(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Credit & Margin Overrides - %s') % self.name,
            'res_model': 'credit.override.request',
            'view_mode': 'list,kanban,form',
            'domain': [('partner_id', 'child_of', self.id)],
            'context': {'default_partner_id': self.id},
        }
