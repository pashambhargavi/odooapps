# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _default_commission_plan_id(self):
        try:
            user = self.env.user
            if 'commission_plan_id' in user._fields and user.commission_plan_id:
                return user.commission_plan_id
            return self.env['commission.plan'].search(
                [('company_id', '=', self.env.company.id)], order='sequence, id', limit=1
            )
        except Exception:
            return False

    commission_plan_id = fields.Many2one(
        'commission.plan', string='Commission Plan',
        default=_default_commission_plan_id, tracking=True,
    )
    sales_manager_id = fields.Many2one(
        'res.users', string='Sales Manager / Lead',
        tracking=True, help='Receives manager override incentive if enabled in the plan.',
    )
    referral_agent_id = fields.Many2one(
        'res.partner', string='Referral Partner / Agent',
        tracking=True, help='External agent or consultant receiving commission on this deal.',
    )

    salesperson_commission_amount = fields.Monetary(
        string='Salesperson Commission', currency_field='currency_id',
        compute='_compute_order_commissions', store=True,
    )
    manager_commission_amount = fields.Monetary(
        string='Manager Override Commission', currency_field='currency_id',
        compute='_compute_order_commissions', store=True,
    )
    total_commission_amount = fields.Monetary(
        string='Total Order Commission', currency_field='currency_id',
        compute='_compute_order_commissions', store=True,
    )

    commission_line_ids = fields.One2many(
        'commission.line', 'sale_order_id', string='Accrued Commission Lines',
    )
    commission_line_count = fields.Integer(
        string='Commissions Count', compute='_compute_commission_line_count',
    )

    @api.onchange('user_id')
    def _onchange_user_id_commission_plan(self):
        if self.user_id and self.user_id.commission_plan_id:
            self.commission_plan_id = self.user_id.commission_plan_id
        if self.user_id and self.user_id.sale_team_id and self.user_id.sale_team_id.user_id:
            self.sales_manager_id = self.user_id.sale_team_id.user_id

    def _compute_commission_line_count(self):
        for order in self:
            order.commission_line_count = len(order.commission_line_ids)

    @api.depends('order_line.price_subtotal', 'commission_plan_id', 'commission_plan_id.flat_rate',
                 'commission_plan_id.plan_type', 'commission_plan_id.margin_rate',
                 'commission_plan_id.manager_override_rate', 'sales_manager_id')
    def _compute_order_commissions(self):
        for order in self:
            plan = order.commission_plan_id
            if not plan:
                order.salesperson_commission_amount = 0.0
                order.manager_commission_amount = 0.0
                order.total_commission_amount = 0.0
                continue

            sp_total = 0.0
            for line in order.order_line.filtered(lambda l: not l.display_type):
                # Standard cost lookup if available
                unit_cost = getattr(line, 'purchase_price', 0.0) or (line.product_id.standard_price if line.product_id else 0.0)
                cost = unit_cost * line.product_uom_qty
                amt, _rate = plan.compute_commission_for_line(line.price_subtotal, cost=cost, product=line.product_id)
                sp_total += amt

            mgr_total = 0.0
            if plan.enable_manager_override and order.sales_manager_id and plan.manager_override_rate:
                mgr_total = order.amount_untaxed * (plan.manager_override_rate / 100.0)

            order.salesperson_commission_amount = sp_total
            order.manager_commission_amount = mgr_total
            order.total_commission_amount = sp_total + mgr_total

    def _create_commission_lines(self, trigger_source='so'):
        """Create commission.line records based on current order lines."""
        comm_line_obj = self.env['commission.line']
        for order in self:
            plan = order.commission_plan_id
            if not plan:
                continue

            # 1. Direct Salesperson Commission Lines
            if order.user_id and order.salesperson_commission_amount > 0:
                comm_line_obj.create({
                    'name': _('Sales Commission: %s (Order %s)') % (order.partner_id.name, order.name),
                    'date': fields.Date.context_today(order),
                    'company_id': order.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'salesperson',
                    'salesperson_id': order.user_id.id,
                    'sale_order_id': order.id,
                    'partner_id': order.partner_id.id,
                    'base_amount': order.amount_untaxed,
                    'rate': (order.salesperson_commission_amount / order.amount_untaxed * 100.0) if order.amount_untaxed else plan.flat_rate,
                    'commission_amount': order.salesperson_commission_amount,
                    'state': 'draft',
                })

            # 2. Manager Override Commission Line
            if plan.enable_manager_override and order.sales_manager_id and order.manager_commission_amount > 0:
                comm_line_obj.create({
                    'name': _('Manager Override Bonus: %s (Order %s)') % (order.user_id.name, order.name),
                    'date': fields.Date.context_today(order),
                    'company_id': order.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'manager',
                    'salesperson_id': order.sales_manager_id.id,
                    'sale_order_id': order.id,
                    'partner_id': order.partner_id.id,
                    'base_amount': order.amount_untaxed,
                    'rate': plan.manager_override_rate,
                    'commission_amount': order.manager_commission_amount,
                    'state': 'draft',
                })

            # 3. External Agent / Referral Partner Commission Line
            if order.referral_agent_id and plan.flat_rate:
                agent_comm = order.amount_untaxed * (plan.flat_rate / 100.0)
                comm_line_obj.create({
                    'name': _('Referral Partner Commission: Order %s') % order.name,
                    'date': fields.Date.context_today(order),
                    'company_id': order.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'partner',
                    'agent_partner_id': order.referral_agent_id.id,
                    'sale_order_id': order.id,
                    'partner_id': order.partner_id.id,
                    'base_amount': order.amount_untaxed,
                    'rate': plan.flat_rate,
                    'commission_amount': agent_comm,
                    'state': 'draft',
                })

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            if order.commission_plan_id and order.commission_plan_id.calculation_basis == 'so_confirm':
                order._create_commission_lines(trigger_source='so')
        return res

    def action_view_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Lines - %s') % self.name,
            'res_model': 'commission.line',
            'view_mode': 'list,kanban,form',
            'domain': [('sale_order_id', '=', self.id)],
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }
