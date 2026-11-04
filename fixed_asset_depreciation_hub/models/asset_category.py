# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FixedAssetCategory(models.Model):
    _name = 'fixed.asset.category'
    _description = 'Fixed Asset Category'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one(
        'account.journal', string='Depreciation Journal', required=True, check_company=True,
        domain="[('type', '=', 'general')]",
    )
    account_asset_id = fields.Many2one(
        'account.account', string='Asset Account', required=True, domain="[('company_ids', 'parent_of', company_id)]",
        help='Balance sheet account holding the gross value of the asset.',
    )
    account_depreciation_id = fields.Many2one(
        'account.account', string='Accumulated Depreciation Account', required=True, domain="[('company_ids', 'parent_of', company_id)]",
        help='Contra-asset account credited by each depreciation entry.',
    )
    account_expense_id = fields.Many2one(
        'account.account', string='Depreciation Expense Account', required=True, domain="[('company_ids', 'parent_of', company_id)]",
        help='Profit & loss account debited by each depreciation entry.',
    )
    account_loss_id = fields.Many2one(
        'account.account', string='Disposal Loss Account', domain="[('company_ids', 'parent_of', company_id)]",
        help='Account debited with the remaining net book value when an asset is disposed.',
    )
    method = fields.Selection([
        ('linear', 'Linear (Straight Line)'),
        ('degressive', 'Declining Balance'),
    ], required=True, default='linear')
    degressive_factor = fields.Float(
        string='Declining Factor', default=2.0,
        help='Factor applied to the linear rate. 2.0 = double declining balance.',
    )
    method_number = fields.Integer(string='Number of Periods', required=True, default=60)
    method_period = fields.Selection([
        ('1', 'Months'),
        ('12', 'Years'),
    ], string='Period Length', required=True, default='1')
    prorata = fields.Boolean(
        string='Prorata Temporis',
        help='Depreciate the first period only for the days remaining after the start date.',
    )
    auto_confirm = fields.Boolean(
        string='Auto-Confirm Assets from Bills',
        help='Assets created from vendor bills are confirmed and their board computed immediately.',
    )
    asset_count = fields.Integer(compute='_compute_asset_count')

    def _compute_asset_count(self):
        data = self.env['fixed.asset']._read_group(
            [('category_id', 'in', self.ids)], ['category_id'], ['__count'])
        counts = {category.id: count for category, count in data}
        for category in self:
            category.asset_count = counts.get(category.id, 0)

    @api.constrains('method_number', 'degressive_factor')
    def _check_method_values(self):
        for category in self:
            if category.method_number <= 0:
                raise ValidationError(_('The number of periods must be greater than zero.'))
            if category.method == 'degressive' and category.degressive_factor <= 0:
                raise ValidationError(_('The declining factor must be greater than zero.'))

    def action_view_assets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('fixed_asset_depreciation_hub.action_fixed_asset')
        action['domain'] = [('category_id', '=', self.id)]
        action['context'] = {'default_category_id': self.id}
        return action
