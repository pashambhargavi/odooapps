# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_commission_agent = fields.Boolean(
        string='Is Commission Agent / Partner', default=False,
        help='Check if this partner acts as an external sales agent, consultant, or affiliate.',
    )
    commission_plan_id = fields.Many2one(
        'commission.plan', string='Assigned Commission Plan',
        tracking=True,
    )
    total_commission_earned = fields.Monetary(
        string='Total Commission Earned', currency_field='currency_id',
        compute='_compute_commission_metrics',
    )
    commission_line_count = fields.Integer(
        string='Commission Lines Count', compute='_compute_commission_metrics',
    )

    def _compute_commission_metrics(self):
        for partner in self:
            lines = self.env['commission.line'].search([
                ('agent_partner_id', 'child_of', partner.id),
                ('state', '!=', 'cancel'),
            ])
            partner.total_commission_earned = sum(lines.mapped('commission_amount'))
            partner.commission_line_count = len(lines)

    def action_view_agent_commissions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Agent Commissions - %s') % self.name,
            'res_model': 'commission.line',
            'view_mode': 'list,kanban,form,pivot,graph',
            'domain': [('agent_partner_id', 'child_of', self.id)],
            'context': {'default_agent_partner_id': self.id},
        }


class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_plan_id = fields.Many2one(
        'commission.plan', string='Sales Commission Plan',
    )
    currency_id = fields.Many2one(
        'res.currency', related='company_id.currency_id', readonly=True,
    )
    total_commission_earned = fields.Monetary(
        string='Total Commission Earned', currency_field='currency_id',
        compute='_compute_user_commission_metrics',
    )
    commission_worksheet_count = fields.Integer(
        string='Worksheets Count', compute='_compute_user_commission_metrics',
    )

    def _compute_user_commission_metrics(self):
        for user in self:
            lines = self.env['commission.line'].search([
                ('salesperson_id', '=', user.id),
                ('state', '!=', 'cancel'),
            ])
            worksheets = self.env['commission.worksheet'].search([
                ('salesperson_id', '=', user.id),
            ])
            user.total_commission_earned = sum(lines.mapped('commission_amount'))
            user.commission_worksheet_count = len(worksheets)

    def action_view_user_worksheets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission Worksheets - %s') % self.name,
            'res_model': 'commission.worksheet',
            'view_mode': 'list,kanban,form',
            'domain': [('salesperson_id', '=', self.id)],
            'context': {'default_salesperson_id': self.id},
        }
