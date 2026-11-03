# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreditRiskPolicy(models.Model):
    _name = 'credit.risk.policy'
    _description = 'Customer Credit, Overdue & Margin Risk Policy'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(string='Policy Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color Index', default=0)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    enforcement_mode = fields.Selection([
        ('allow', 'No Block (Monitor Only)'),
        ('warning', 'Soft Warning Banner Only'),
        ('block', 'Strict Block (Require Credit/Margin Override)'),
    ], string='Enforcement Mode', default='block', required=True)

    default_credit_limit = fields.Monetary(
        string='Default Credit Limit',
        currency_field='currency_id', default=10000.0, required=True,
        help='Maximum total receivable + uninvoiced sales order exposure allowed.',
    )
    check_overdue_aging = fields.Boolean(
        string='Block on Overdue Invoices', default=True,
    )
    max_overdue_days = fields.Integer(
        string='Max Allowed Overdue Days', default=30, required=True,
        help='Block new orders if the customer has any unpaid invoice overdue by more than this many days.',
    )
    max_overdue_invoices = fields.Integer(
        string='Max Allowed Overdue Invoices', default=2, required=True,
        help='Block new orders if the number of overdue unpaid invoices exceeds this count.',
    )
    check_minimum_margin = fields.Boolean(
        string='Enforce Minimum Profit Margin %', default=True,
    )
    min_margin_percent = fields.Float(
        string='Minimum Order Margin (%)', default=15.0, required=True,
        help='Require override if the Sales Order overall profit margin % is below this threshold.',
    )
    auto_confirm_on_override = fields.Boolean(
        string='Auto-Confirm Order on Override Approval',
        default=True,
    )
    approver_ids = fields.Many2many(
        'res.users',
        'credit_risk_policy_res_users_rel',
        'policy_id', 'user_id',
        string='Credit & Margin Controllers',
        domain="[('share', '=', False)]",
    )
    partner_ids = fields.One2many('res.partner', 'credit_policy_id', string='Assigned Customers')
    partner_count = fields.Integer(string='Customers Count', compute='_compute_counts')
    pending_override_count = fields.Integer(string='Pending Overrides', compute='_compute_counts')
    description = fields.Text(string='Policy Description', translate=True)

    def _compute_counts(self):
        for policy in self:
            policy.partner_count = len(policy.partner_ids)
            policy.pending_override_count = self.env['credit.override.request'].search_count([
                ('policy_id', '=', policy.id),
                ('state', '=', 'pending'),
            ])

    @api.constrains('default_credit_limit', 'max_overdue_days', 'max_overdue_invoices')
    def _check_thresholds(self):
        for policy in self:
            if policy.default_credit_limit < 0:
                raise ValidationError(_('Default Credit Limit cannot be negative.'))
            if policy.max_overdue_days < 0 or policy.max_overdue_invoices < 0:
                raise ValidationError(_('Overdue thresholds cannot be negative.'))

    def action_view_assigned_partners(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s - Customers') % self.name,
            'res_model': 'res.partner',
            'view_mode': 'list,kanban,form',
            'domain': [('credit_policy_id', '=', self.id)],
            'context': {'default_credit_policy_id': self.id},
        }

    def action_view_pending_overrides(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('%s - Override Requests') % self.name,
            'res_model': 'credit.override.request',
            'view_mode': 'list,kanban,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'default_policy_id': self.id, 'search_default_filter_pending': 1},
        }
