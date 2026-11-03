# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CommissionPlan(models.Model):
    _name = 'commission.plan'
    _description = 'Sales Commission & Incentive Plan'
    _order = 'sequence, name, id'
    _check_company_auto = True

    name = fields.Char(string='Plan Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )

    plan_type = fields.Selection([
        ('flat', 'Flat Percentage on Revenue'),
        ('tiered', 'Progressive Revenue Tiers'),
        ('margin', 'Gross Profit Margin Percentage'),
        ('product_rule', 'Product & Category Specific Rates'),
    ], string='Commission Calculation Method', default='flat', required=True)

    calculation_basis = fields.Selection([
        ('so_confirm', 'On Sales Order Confirmation'),
        ('inv_post', 'On Customer Invoice Posted'),
        ('inv_paid', 'On Customer Invoice Paid (Cash Collection)'),
    ], string='Commission Trigger Event', default='inv_paid', required=True,
       help='Cash collection trigger ensures sales reps are rewarded only when the company actually collects customer payment.')

    flat_rate = fields.Float(
        string='Direct Commission Rate (%)', default=5.0,
        help='Percentage of base amount credited to the assigned salesperson.',
    )
    margin_rate = fields.Float(
        string='Margin Commission Rate (%)', default=15.0,
        help='Percentage of gross profit margin credited to the salesperson.',
    )
    enable_manager_override = fields.Boolean(
        string='Enable Manager Override Commission', default=True,
    )
    manager_override_rate = fields.Float(
        string='Manager Override Rate (%)', default=1.5,
        help='Override bonus paid to the sales team leader or manager on total closed deals.',
    )

    tier_ids = fields.One2many(
        'commission.plan.tier', 'plan_id', string='Revenue Volume Tiers', copy=True,
    )
    rule_ids = fields.One2many(
        'commission.plan.rule', 'plan_id', string='Product / Category Rules', copy=True,
    )

    user_ids = fields.One2many('res.users', 'commission_plan_id', string='Assigned Sales Reps')
    partner_ids = fields.One2many('res.partner', 'commission_plan_id', string='Assigned Agents & Partners')
    user_count = fields.Integer(string='Reps Count', compute='_compute_counts')
    commission_line_count = fields.Integer(string='Commission Lines Count', compute='_compute_counts')
    description = fields.Text(string='Plan Terms & Guidelines', translate=True)

    def _compute_counts(self):
        for plan in self:
            plan.user_count = len(plan.user_ids) + len(plan.partner_ids)
            plan.commission_line_count = self.env['commission.line'].search_count([('plan_id', '=', plan.id)])

    @api.constrains('flat_rate', 'margin_rate', 'manager_override_rate')
    def _check_rates(self):
        for plan in self:
            if plan.flat_rate < 0 or plan.margin_rate < 0 or plan.manager_override_rate < 0:
                raise ValidationError(_('Commission rates cannot be negative.'))

    def compute_commission_for_line(self, subtotal, cost=0.0, product=None):
        """Compute direct commission amount and effective rate for a sales order or invoice line."""
        self.ensure_one()
        margin = max(subtotal - cost, 0.0)

        if self.plan_type == 'flat':
            rate = self.flat_rate
            amt = subtotal * (rate / 100.0)
            return amt, rate

        elif self.plan_type == 'margin':
            rate = self.margin_rate
            amt = margin * (rate / 100.0)
            effective_rate = (amt / subtotal * 100.0) if subtotal else 0.0
            return amt, effective_rate

        elif self.plan_type == 'tiered':
            # Check matching volume tier
            matched_tier = self.tier_ids.filtered(
                lambda t: (t.amount_from <= subtotal) and (t.amount_to == 0.0 or subtotal <= t.amount_to)
            )[:1]
            if matched_tier:
                rate = matched_tier.rate
                return subtotal * (rate / 100.0), rate
            rate = self.flat_rate
            return subtotal * (rate / 100.0), rate

        elif self.plan_type == 'product_rule' and product:
            rule = self.rule_ids.filtered(lambda r: r.product_id == product)[:1]
            if not rule and product.categ_id:
                rule = self.rule_ids.filtered(lambda r: r.category_id == product.categ_id)[:1]
            if rule:
                rate = rule.rate
                return subtotal * (rate / 100.0), rate
            rate = self.flat_rate
            return subtotal * (rate / 100.0), rate

        return subtotal * (self.flat_rate / 100.0), self.flat_rate

    def action_view_commission_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Lines - %s') % self.name,
            'res_model': 'commission.line',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': [('plan_id', '=', self.id)],
            'context': {'default_plan_id': self.id},
        }


class CommissionPlanTier(models.Model):
    _name = 'commission.plan.tier'
    _description = 'Commission Revenue Tier'
    _order = 'amount_from, id'

    plan_id = fields.Many2one('commission.plan', string='Plan', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='plan_id.company_id', store=True)
    currency_id = fields.Many2one(related='plan_id.currency_id', store=True)

    amount_from = fields.Monetary(string='From Amount', required=True, currency_field='currency_id')
    amount_to = fields.Monetary(
        string='To Amount', required=True, currency_field='currency_id',
        help='Set 0 for unlimited upper threshold.',
    )
    rate = fields.Float(string='Commission Rate (%)', required=True, default=5.0)


class CommissionPlanRule(models.Model):
    _name = 'commission.plan.rule'
    _description = 'Commission Product / Category Rule'
    _order = 'id'

    plan_id = fields.Many2one('commission.plan', string='Plan', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='plan_id.company_id', store=True)

    product_id = fields.Many2one('product.product', string='Product')
    category_id = fields.Many2one('product.category', string='Product Category')
    rate = fields.Float(string='Commission Rate (%)', required=True, default=5.0)

    @api.constrains('product_id', 'category_id')
    def _check_target(self):
        for rule in self:
            if not rule.product_id and not rule.category_id:
                raise ValidationError(_('Please specify either a Product or a Product Category for the rule.'))
