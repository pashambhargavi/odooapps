# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    subscription_id = fields.Many2one(
        'subscription.contract', string='Linked Subscription Contract',
        copy=False, readonly=True,
    )
    subscription_plan_id = fields.Many2one(
        'subscription.plan', string='Subscription Billing Plan',
        help='Select a recurring plan to convert this order into a recurring contract upon confirmation.',
    )

    def action_create_subscription(self):
        """Converts confirmed sales order into a recurring subscription contract."""
        self.ensure_one()
        if self.subscription_id:
            raise UserError(_('A subscription contract (%s) is already created for this order.') % self.subscription_id.name)

        if not self.subscription_plan_id:
            # Fallback to default active plan
            default_plan = self.env['subscription.plan'].search(
                [('company_id', '=', self.company_id.id)], limit=1
            )
            if not default_plan:
                raise UserError(_('Please select a Subscription Billing Plan on the order or create one first.'))
            plan = default_plan
        else:
            plan = self.subscription_plan_id

        contract_lines = []
        for line in self.order_line.filtered(lambda l: not l.display_type and l.product_id):
            uom = getattr(line, 'product_uom_id', None) or getattr(line, 'product_uom', None) or line.product_id.uom_id
            taxes = getattr(line, 'tax_id', None) or getattr(line, 'tax_ids', False) or self.env['account.tax']
            contract_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'quantity': line.product_uom_qty,
                'product_uom_id': uom.id if uom else False,
                'price_unit': line.price_unit,
                'discount': line.discount,
                'tax_ids': [(6, 0, taxes.ids if taxes else [])],
            }))

        if not contract_lines:
            raise UserError(_('The order does not contain valid order lines to convert.'))

        contract = self.env['subscription.contract'].create({
            'partner_id': self.partner_id.id,
            'plan_id': plan.id,
            'company_id': self.company_id.id,
            'user_id': self.user_id.id or self.env.user.id,
            'date_start': fields.Date.context_today(self),
            'next_invoice_date': fields.Date.context_today(self),
            'line_ids': contract_lines,
            'notes': _('Generated from Sales Order %s') % self.name,
        })
        self.subscription_id = contract.id
        contract.action_activate()

        return {
            'name': _('Subscription Contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.contract',
            'view_mode': 'form',
            'res_id': contract.id,
        }

    def action_view_subscription(self):
        self.ensure_one()
        return {
            'name': _('Subscription Contract'),
            'type': 'ir.actions.act_window',
            'res_model': 'subscription.contract',
            'view_mode': 'form',
            'res_id': self.subscription_id.id,
        }
