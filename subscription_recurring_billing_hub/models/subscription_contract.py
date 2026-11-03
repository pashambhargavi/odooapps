# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SubscriptionContract(models.Model):
    _name = 'subscription.contract'
    _description = 'Subscription Contract & Recurring Billing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Contract Reference', required=True, copy=False, readonly=True,
        default=lambda self: _('New'), tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
    plan_id = fields.Many2one(
        'subscription.plan', string='Subscription Plan', required=True, tracking=True,
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active / In Progress'),
        ('paused', 'Paused'),
        ('expired', 'Expired'),
        ('closed', 'Closed / Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    date_start = fields.Date(
        string='Start Date', default=fields.Date.context_today, required=True, tracking=True,
    )
    date_end = fields.Date(
        string='Expiration / End Date', tracking=True,
        help='Optional expiry date. If empty, the subscription renews indefinitely until cancelled.',
    )
    next_invoice_date = fields.Date(
        string='Next Invoice Date', default=fields.Date.context_today, tracking=True,
    )
    last_invoice_date = fields.Date(
        string='Last Invoiced Date', readonly=True, copy=False,
    )
    user_id = fields.Many2one(
        'res.users', string='Account Executive',
        default=lambda self: self.env.user, tracking=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='company_id.currency_id', readonly=True,
    )
    line_ids = fields.One2many(
        'subscription.contract.line', 'contract_id', string='Subscription Lines', copy=True,
    )
    invoice_ids = fields.One2many(
        'account.move', 'subscription_id', string='Generated Invoices', readonly=True,
    )
    invoice_count = fields.Integer(
        string='Invoices Count', compute='_compute_invoice_count',
    )

    amount_untaxed = fields.Monetary(
        string='Untaxed Amount', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    amount_tax = fields.Monetary(
        string='Taxes', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    amount_total = fields.Monetary(
        string='Recurring Cycle Total', compute='_compute_amounts', store=True, currency_field='currency_id',
    )
    mrr = fields.Monetary(
        string='MRR', compute='_compute_recurring_metrics', store=True, currency_field='currency_id',
        help='Monthly Recurring Revenue normalized from billing cycle.',
    )
    arr = fields.Monetary(
        string='ARR', compute='_compute_recurring_metrics', store=True, currency_field='currency_id',
        help='Annual Recurring Revenue (MRR x 12).',
    )

    notes = fields.Html(string='Internal Notes')
    close_reason = fields.Text(string='Cancellation / Closure Reason', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.contract') or _('New')
        return super().create(vals_list)

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for contract in self:
            contract.invoice_count = len(contract.invoice_ids)

    @api.depends('line_ids.price_subtotal', 'line_ids.price_total')
    def _compute_amounts(self):
        for contract in self:
            contract.amount_untaxed = sum(contract.line_ids.mapped('price_subtotal'))
            contract.amount_total = sum(contract.line_ids.mapped('price_total'))
            contract.amount_tax = contract.amount_total - contract.amount_untaxed

    @api.depends('amount_untaxed', 'plan_id.billing_interval', 'plan_id.billing_interval_count')
    def _compute_recurring_metrics(self):
        for contract in self:
            plan = contract.plan_id
            count = plan.billing_interval_count or 1
            interval = plan.billing_interval or 'month'
            amt = contract.amount_untaxed or 0.0

            # Normalize to Monthly Recurring Revenue (MRR)
            if interval == 'month':
                mrr_val = amt / count
            elif interval == 'year':
                mrr_val = amt / (count * 12.0)
            elif interval == 'week':
                mrr_val = (amt * 52.0) / (count * 12.0)
            elif interval == 'day':
                mrr_val = (amt * 30.0) / count
            else:
                mrr_val = amt

            contract.mrr = mrr_val
            contract.arr = mrr_val * 12.0

    # Lifecycle Actions
    def action_activate(self):
        for contract in self:
            if not contract.line_ids:
                raise UserError(_('Please add at least one subscription item line before activating.'))
            if not contract.next_invoice_date:
                contract.next_invoice_date = contract.date_start or fields.Date.context_today(contract)
            contract.state = 'active'
            contract.message_post(body=_('Subscription contract has been activated and scheduled for billing.'))

    def action_pause(self):
        for contract in self:
            contract.state = 'paused'
            contract.message_post(body=_('Subscription contract billing has been paused.'))

    def action_resume(self):
        for contract in self:
            contract.state = 'active'
            contract.message_post(body=_('Subscription contract billing has been resumed.'))

    def action_close(self):
        for contract in self:
            contract.state = 'closed'
            contract.message_post(body=_('Subscription contract has been terminated / closed.'))

    def action_open_renew_wizard(self):
        self.ensure_one()
        return {
            'name': _('Renew / Extend Subscription'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_contract_id': self.id,
                'default_current_end_date': self.date_end,
                'default_plan_id': self.plan_id.id,
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        return {
            'name': _('Subscription Invoices - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,kanban,form',
            'domain': [('subscription_id', '=', self.id)],
            'context': {'default_subscription_id': self.id, 'default_move_type': 'out_invoice'},
        }

    def _calculate_next_date(self, base_date, plan):
        count = plan.billing_interval_count or 1
        unit = plan.billing_interval or 'month'
        if unit == 'day':
            return base_date + relativedelta(days=count)
        elif unit == 'week':
            return base_date + relativedelta(weeks=count)
        elif unit == 'month':
            return base_date + relativedelta(months=count)
        elif unit == 'year':
            return base_date + relativedelta(years=count)
        return base_date + relativedelta(months=1)

    def action_generate_invoice(self):
        """Generates a customer invoice for the active subscription cycle."""
        created_invoices = self.env['account.move']
        for contract in self:
            if not contract.line_ids:
                raise UserError(_('Contract %s has no subscription lines.') % contract.name)

            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': contract.partner_id.id,
                'currency_id': contract.currency_id.id,
                'company_id': contract.company_id.id,
                'invoice_user_id': contract.user_id.id,
                'invoice_date': fields.Date.context_today(contract),
                'subscription_id': contract.id,
                'narration': _('Recurring billing for subscription %s (%s)') % (
                    contract.name, contract.plan_id.name
                ),
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'name': _('%s - Subscription Billing (%s)') % (line.name, contract.name),
                        'quantity': line.quantity,
                        'product_uom_id': line.product_uom_id.id,
                        'price_unit': line.price_unit,
                        'discount': line.discount,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                    }) for line in contract.line_ids
                ],
            }
            invoice = self.env['account.move'].create(invoice_vals)

            if contract.plan_id.auto_post_invoice and invoice.state == 'draft':
                try:
                    invoice.action_post()
                except Exception:
                    pass

            # Update dates
            current_inv_date = contract.next_invoice_date or fields.Date.context_today(contract)
            contract.last_invoice_date = current_inv_date
            next_date = self._calculate_next_date(current_inv_date, contract.plan_id)

            # Check if expiry reached
            if contract.date_end and next_date > contract.date_end:
                contract.next_invoice_date = False
                contract.state = 'expired'
                contract.message_post(body=_('Subscription reached its end date (%s) and marked as Expired.') % contract.date_end)
            else:
                contract.next_invoice_date = next_date

            contract.message_post(body=_('Generated recurring invoice %s.') % invoice.name)
            created_invoices |= invoice

        if len(created_invoices) == 1:
            return {
                'name': _('Customer Invoice'),
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': created_invoices.id,
            }
        return contract.action_view_invoices()

    # CRON Schedulers
    @api.model
    def cron_subscription_recurring_invoicing(self):
        """Automated daily cron to generate recurring invoices on due date."""
        today = fields.Date.context_today(self)
        contracts = self.search([
            ('state', '=', 'active'),
            ('plan_id.auto_invoice', '=', True),
            ('next_invoice_date', '<=', today),
        ])
        for contract in contracts:
            try:
                contract.action_generate_invoice()
            except Exception as e:
                contract.message_post(
                    body=_('Automatic invoice generation failed: %s') % str(e)
                )

    @api.model
    def cron_subscription_expiration_alerts(self):
        """Automated cron checking for contracts expiring within alert window."""
        today = fields.Date.context_today(self)
        plans = self.env['subscription.plan'].search([('reminder_days_before', '>', 0)])
        for plan in plans:
            threshold_date = today + relativedelta(days=plan.reminder_days_before)
            contracts = self.search([
                ('plan_id', '=', plan.id),
                ('state', '=', 'active'),
                ('date_end', '=', threshold_date),
            ])
            for contract in contracts:
                contract.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=contract.user_id.id or self.env.user.id,
                    summary=_('Subscription %s Expiring Soon') % contract.name,
                    note=_('Contract expires in %d days on %s. Contact client for renewal.') % (
                        plan.reminder_days_before, contract.date_end
                    ),
                )


class SubscriptionContractLine(models.Model):
    _name = 'subscription.contract.line'
    _description = 'Subscription Contract Line'
    _order = 'sequence, id'

    contract_id = fields.Many2one(
        'subscription.contract', string='Contract', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one(
        'product.product', string='Product / Service', required=True,
    )
    name = fields.Text(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure',
    )
    price_unit = fields.Float(string='Unit Price', required=True, default=0.0)
    discount = fields.Float(string='Discount (%)', default=0.0)
    tax_ids = fields.Many2many(
        'account.tax', string='Taxes',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency', related='contract_id.currency_id', readonly=True,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal', compute='_compute_line_totals', store=True, currency_field='currency_id',
    )
    price_total = fields.Monetary(
        string='Total', compute='_compute_line_totals', store=True, currency_field='currency_id',
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.name = self.product_id.get_product_multiline_description_sale() if hasattr(self.product_id, 'get_product_multiline_description_sale') else self.product_id.name
        self.price_unit = self.product_id.list_price
        self.product_uom_id = self.product_id.uom_id
        if self.product_id.taxes_id:
            self.tax_ids = self.product_id.taxes_id.filtered(
                lambda t: not self.contract_id.company_id or t.company_id == self.contract_id.company_id
            )

    @api.depends('quantity', 'price_unit', 'discount', 'tax_ids')
    def _compute_line_totals(self):
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_ids.compute_all(
                price,
                line.contract_id.currency_id,
                line.quantity,
                product=line.product_id,
                partner=line.contract_id.partner_id,
            )
            line.price_subtotal = taxes['total_excluded']
            line.price_total = taxes['total_included']
