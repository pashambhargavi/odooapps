# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    commission_plan_id = fields.Many2one(
        'commission.plan', string='Commission Plan',
        compute='_compute_commission_plan_id', store=True, readonly=False,
    )
    sales_manager_id = fields.Many2one(
        'res.users', string='Sales Manager / Lead',
        compute='_compute_commission_plan_id', store=True, readonly=False,
    )
    referral_agent_id = fields.Many2one(
        'res.partner', string='Referral Partner / Agent',
        compute='_compute_commission_plan_id', store=True, readonly=False,
    )

    commission_line_ids = fields.One2many(
        'commission.line', 'invoice_id', string='Accrued Commission Lines',
    )
    commission_line_count = fields.Integer(
        string='Commissions Count', compute='_compute_commission_line_count',
    )

    @api.depends('invoice_line_ids.sale_line_ids.order_id')
    def _compute_commission_plan_id(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            sale_orders = move.invoice_line_ids.mapped('sale_line_ids.order_id')
            if sale_orders:
                so = sale_orders[0]
                if so.commission_plan_id:
                    move.commission_plan_id = so.commission_plan_id
                if so.sales_manager_id:
                    move.sales_manager_id = so.sales_manager_id
                if so.referral_agent_id:
                    move.referral_agent_id = so.referral_agent_id
            elif move.invoice_user_id and move.invoice_user_id.commission_plan_id:
                move.commission_plan_id = move.invoice_user_id.commission_plan_id

    def _compute_commission_line_count(self):
        for move in self:
            move.commission_line_count = len(move.commission_line_ids)

    def _create_invoice_commission_lines(self):
        comm_line_obj = self.env['commission.line']
        for move in self:
            if move.move_type != 'out_invoice' or not move.commission_plan_id:
                continue
            if move.commission_line_ids:
                # Already generated
                continue

            plan = move.commission_plan_id
            sp_total = 0.0
            for line in move.invoice_line_ids.filtered(lambda l: not l.display_type):
                cost = (line.product_id.standard_price if line.product_id else 0.0) * line.quantity
                amt, _rate = plan.compute_commission_for_line(line.price_subtotal, cost=cost, product=line.product_id)
                sp_total += amt

            mgr_total = 0.0
            if plan.enable_manager_override and move.sales_manager_id and plan.manager_override_rate:
                mgr_total = move.amount_untaxed * (plan.manager_override_rate / 100.0)

            # Direct sales rep commission
            if move.invoice_user_id and sp_total > 0:
                comm_line_obj.create({
                    'name': _('Invoice Commission: %s (%s)') % (move.partner_id.name, move.name),
                    'date': move.invoice_date or fields.Date.context_today(move),
                    'company_id': move.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'salesperson',
                    'salesperson_id': move.invoice_user_id.id,
                    'invoice_id': move.id,
                    'partner_id': move.partner_id.id,
                    'base_amount': move.amount_untaxed,
                    'rate': (sp_total / move.amount_untaxed * 100.0) if move.amount_untaxed else plan.flat_rate,
                    'commission_amount': sp_total,
                    'state': 'draft',
                })

            # Manager override commission
            if mgr_total > 0 and move.sales_manager_id:
                comm_line_obj.create({
                    'name': _('Invoice Manager Override: %s (%s)') % (move.invoice_user_id.name, move.name),
                    'date': move.invoice_date or fields.Date.context_today(move),
                    'company_id': move.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'manager',
                    'salesperson_id': move.sales_manager_id.id,
                    'invoice_id': move.id,
                    'partner_id': move.partner_id.id,
                    'base_amount': move.amount_untaxed,
                    'rate': plan.manager_override_rate,
                    'commission_amount': mgr_total,
                    'state': 'draft',
                })

            # Referral partner commission
            if move.referral_agent_id and plan.flat_rate:
                agent_comm = move.amount_untaxed * (plan.flat_rate / 100.0)
                comm_line_obj.create({
                    'name': _('Invoice Referral Partner Commission: %s') % move.name,
                    'date': move.invoice_date or fields.Date.context_today(move),
                    'company_id': move.company_id.id,
                    'plan_id': plan.id,
                    'beneficiary_type': 'partner',
                    'agent_partner_id': move.referral_agent_id.id,
                    'invoice_id': move.id,
                    'partner_id': move.partner_id.id,
                    'base_amount': move.amount_untaxed,
                    'rate': plan.flat_rate,
                    'commission_amount': agent_comm,
                    'state': 'draft',
                })

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.commission_plan_id and move.commission_plan_id.calculation_basis == 'inv_post':
                move._create_invoice_commission_lines()
        return res

    def _compute_payment_state(self):
        super()._compute_payment_state()
        for move in self:
            if move.payment_state in ('paid', 'in_payment') and move.commission_plan_id:
                if move.commission_plan_id.calculation_basis == 'inv_paid':
                    move._create_invoice_commission_lines()

    def action_view_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Lines - %s') % self.name,
            'res_model': 'commission.line',
            'view_mode': 'list,kanban,form',
            'domain': [('invoice_id', '=', self.id)],
            'context': {
                'default_invoice_id': self.id,
                'default_partner_id': self.partner_id.id,
            },
        }
