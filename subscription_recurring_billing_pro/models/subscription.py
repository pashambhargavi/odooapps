# -*- coding: utf-8 -*-
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SubscriptionPro(models.Model):
    _name = 'subscription.pro'
    _description = 'Subscription Contract Pro'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Subscription Ref', readonly=True, copy=False, default=lambda self: _('New'))
    partner_id = fields.Many2one('res.partner', string='Subscriber / Customer', required=True, tracking=True)
    plan_id = fields.Many2one('subscription.plan.pro', string='Subscription Plan', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', readonly=True)
    user_id = fields.Many2one('res.users', string='Account Executive', default=lambda self: self.env.user, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft Quotation'),
        ('trial', 'In Trial'),
        ('active', 'Active & Billing'),
        ('paused', 'Paused / In Dunning'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled / Churned'),
    ], string='Status', default='draft', required=True, tracking=True)

    start_date = fields.Date(string='Contract Start Date', default=fields.Date.today, required=True, tracking=True)
    trial_end_date = fields.Date(string='Trial End Date', readonly=True)
    end_date = fields.Date(string='Contract End Date', help='Leave empty for evergreen auto-renewing subscriptions.')
    next_invoice_date = fields.Date(string='Next Invoicing Date', tracking=True)

    auto_renew = fields.Boolean(string='Auto-Renew', default=True)
    close_reason_id = fields.Many2one('subscription.close.reason', string='Cancellation / Churn Reason', tracking=True)

    line_ids = fields.One2many('subscription.pro.line', 'subscription_id', string='Subscription Items')
    recurring_total = fields.Monetary(string='Recurring Subtotal', compute='_compute_revenue_metrics', store=True)
    recurring_mrr = fields.Monetary(string='Monthly Recurring Revenue (MRR)', compute='_compute_revenue_metrics', store=True, tracking=True)
    recurring_arr = fields.Monetary(string='Annual Recurring Revenue (ARR)', compute='_compute_revenue_metrics', store=True)

    invoice_ids = fields.One2many('account.move', 'subscription_id', string='Recurring Invoices')
    invoice_count = fields.Integer(string='Invoice Count', compute='_compute_invoice_count')

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for sub in self:
            sub.invoice_count = len(sub.invoice_ids)

    @api.depends('line_ids.subtotal', 'plan_id.billing_interval', 'plan_id.billing_interval_count')
    def _compute_revenue_metrics(self):
        for sub in self:
            total = sum(sub.line_ids.mapped('subtotal'))
            sub.recurring_total = total

            if not sub.plan_id:
                sub.recurring_mrr = total
                sub.recurring_arr = total * 12
                continue

            interval = sub.plan_id.billing_interval
            count = max(1, sub.plan_id.billing_interval_count or 1)

            if interval == 'daily':
                mrr = (total / count) * 30.0
            elif interval == 'weekly':
                mrr = (total / count) * 4.333
            elif interval == 'monthly':
                mrr = total / count
            elif interval == 'quarterly':
                mrr = total / (3.0 * count)
            elif interval == 'semi_annual':
                mrr = total / (6.0 * count)
            elif interval == 'annual':
                mrr = total / (12.0 * count)
            else:
                mrr = total

            sub.recurring_mrr = round(mrr, 2)
            sub.recurring_arr = round(mrr * 12.0, 2)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('subscription.pro') or _('New')
        return super().create(vals_list)

    def action_start(self):
        """Activates contract, handles trial periods, and calculates first invoice date."""
        for sub in self:
            if not sub.line_ids:
                raise UserError(_("Please add at least one recurring line item before activating the subscription."))

            today = fields.Date.today()
            start = sub.start_date or today

            if sub.plan_id.trial_period_days > 0 and not sub.trial_end_date:
                sub.trial_end_date = start + relativedelta(days=sub.plan_id.trial_period_days)
                sub.state = 'trial'
                sub.next_invoice_date = sub.trial_end_date
            else:
                sub.state = 'active'
                if not sub.next_invoice_date:
                    sub.next_invoice_date = start

    def action_pause(self):
        self.write({'state': 'paused'})

    def action_resume(self):
        self.write({'state': 'active'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def _get_next_date_from(self, from_date):
        """Computes next date based on subscription plan frequency."""
        self.ensure_one()
        interval = self.plan_id.billing_interval
        count = max(1, self.plan_id.billing_interval_count or 1)

        if interval == 'daily':
            return from_date + relativedelta(days=count)
        elif interval == 'weekly':
            return from_date + relativedelta(weeks=count)
        elif interval == 'monthly':
            return from_date + relativedelta(months=count)
        elif interval == 'quarterly':
            return from_date + relativedelta(months=3 * count)
        elif interval == 'semi_annual':
            return from_date + relativedelta(months=6 * count)
        elif interval == 'annual':
            return from_date + relativedelta(years=count)
        return from_date + relativedelta(months=1)

    def action_generate_invoice(self):
        """Generates Customer Invoice for recurring period and advances next_invoice_date."""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_("No subscription lines to invoice."))

        journal = self.plan_id.invoicing_journal_id or self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)

        inv_date = self.next_invoice_date or fields.Date.today()
        period_end = self._get_next_date_from(inv_date) - relativedelta(days=1)

        invoice_lines = []
        for line in self.line_ids:
            desc = _("%s [Period: %s to %s]") % (line.name or line.product_id.display_name, inv_date, period_end)
            invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': desc,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
            }))

        inv_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'company_id': self.company_id.id,
            'invoice_date': inv_date,
            'journal_id': journal.id if journal else False,
            'subscription_id': self.id,
            'invoice_line_ids': invoice_lines,
        }

        invoice = self.env['account.move'].create(inv_vals)

        # Advance next invoicing date
        self.write({
            'state': 'active',
            'next_invoice_date': self._get_next_date_from(inv_date),
        })

        return invoice

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
        action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        action['context'] = {'default_subscription_id': self.id, 'default_move_type': 'out_invoice'}
        return action

    @api.model
    def _cron_generate_recurring_invoices(self):
        """Automated daily batch runner for all due subscriptions."""
        today = fields.Date.today()
        due_subs = self.search([
            ('state', 'in', ('trial', 'active')),
            ('next_invoice_date', '<=', today)
        ])
        for sub in due_subs:
            try:
                sub.action_generate_invoice()
            except Exception:
                pass


class SubscriptionProLine(models.Model):
    _name = 'subscription.pro.line'
    _description = 'Subscription Item Line'

    subscription_id = fields.Many2one('subscription.pro', string='Subscription', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Plan Service / Product', required=True)
    name = fields.Char(string='Description', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    price_unit = fields.Monetary(string='Recurring Price', required=True)
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='subscription_id.currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.price_unit = self.product_id.list_price

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
