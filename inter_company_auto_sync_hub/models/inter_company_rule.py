# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class InterCompanyRule(models.Model):
    _name = 'inter.company.rule'
    _description = 'Inter-Company Synchronization Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    company_id = fields.Many2one(
        'res.company',
        string='Source Entity',
        required=True,
        default=lambda self: self.env.company,
        index=True
    )
    target_company_id = fields.Many2one(
        'res.company',
        string='Target Sister Entity',
        required=True,
        index=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Sister Entity Vendor/Customer Partner',
        required=True,
        help='Partner in the source company representing the target sister entity.'
    )
    target_partner_id = fields.Many2one(
        'res.partner',
        string='Source Entity Partner in Target Company',
        help='Partner in the target company representing this source company.'
    )

    # Document Sync Switches
    sync_po_to_so = fields.Boolean(
        string='Sync Purchase Order to Sales Order',
        default=True,
        help='When a PO is confirmed in Source Company, auto-create a matching Sales Order in Target Company.'
    )
    auto_confirm_so = fields.Boolean(
        string='Auto-Confirm Generated Sales Order',
        default=False,
        help='Automatically validate and confirm the generated Sales Order in the target entity.'
    )

    sync_so_to_po = fields.Boolean(
        string='Sync Sales Order to Purchase Order',
        default=False,
        help='When a SO is confirmed in Source Company, auto-create a matching Purchase Order in Target Company.'
    )
    auto_confirm_po = fields.Boolean(
        string='Auto-Confirm Generated Purchase Order',
        default=False,
        help='Automatically validate and confirm the generated Purchase Order in the target entity.'
    )

    sync_invoice_to_bill = fields.Boolean(
        string='Sync Customer Invoice to Vendor Bill',
        default=True,
        help='When a Customer Invoice is posted to the sister company, auto-create a matching Vendor Bill in the sister company.'
    )
    auto_validate_bill = fields.Boolean(
        string='Auto-Post Generated Vendor Bill',
        default=False,
        help='Automatically post the mirrored Vendor Bill in the target company.'
    )

    sync_delivery_to_receipt = fields.Boolean(
        string='Sync Delivery Order to Stock Receipt',
        default=True,
        help='When a Delivery Order is validated in the source company, update or create the matching incoming receipt in the target company.'
    )
    auto_validate_receipt = fields.Boolean(
        string='Auto-Validate Mirrored Receipt',
        default=False,
        help='Automatically validate the mirrored stock receipt when the delivery completes.'
    )

    # Pricing & Margin Rules
    pricing_rule = fields.Selection([
        ('original_price', 'Same Original Transaction Price'),
        ('cost_plus_margin', 'Cost-Plus Margin Markup %'),
        ('discount_from_list', 'Discount from Public Catalog Price %'),
        ('custom_pricelist', 'Dedicated Inter-Company Pricelist'),
    ], string='Transfer Pricing Rule', default='original_price', required=True)

    margin_percent = fields.Float(
        string='Markup Margin (%)',
        default=10.0,
        help='Percentage added over standard cost (e.g. 15.0 for cost + 15%).'
    )
    discount_percent = fields.Float(
        string='Discount (%)',
        default=10.0,
        help='Percentage deducted from standard public catalog price.'
    )
    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Inter-Company Pricelist',
        help='Specific pricelist used when calculating inter-company sales lines.'
    )

    elimination_code = fields.Char(
        string='Inter-Company Elimination Code',
        default='IC-ELIM-01',
        help='Accounting elimination reference code for consolidated group financial statements.'
    )

    log_ids = fields.One2many(
        'inter.company.log',
        'rule_id',
        string='Execution Logs'
    )
    log_count = fields.Integer(
        string='Log Count',
        compute='_compute_log_count'
    )

    @api.depends('log_ids')
    def _compute_log_count(self):
        for rec in self:
            rec.log_count = len(rec.log_ids)

    @api.constrains('company_id', 'target_company_id')
    def _check_different_companies(self):
        for rec in self:
            if rec.company_id and rec.target_company_id and rec.company_id == rec.target_company_id:
                raise ValidationError(_('Source and Target entities cannot be the same company.'))

    def calculate_transfer_price(self, product, base_price=0.0):
        """Calculate unit transfer price based on the configured pricing rule."""
        self.ensure_one()
        if self.pricing_rule == 'original_price':
            return base_price if base_price > 0.0 else product.standard_price

        elif self.pricing_rule == 'cost_plus_margin':
            cost = product.standard_price or base_price
            markup = cost * (self.margin_percent / 100.0)
            return cost + markup

        elif self.pricing_rule == 'discount_from_list':
            catalog_price = product.list_price or base_price
            discount = catalog_price * (self.discount_percent / 100.0)
            return max(0.0, catalog_price - discount)

        elif self.pricing_rule == 'custom_pricelist' and self.pricelist_id:
            return self.pricelist_id._get_product_price(product, 1.0) or base_price

        return base_price or product.standard_price

    def action_view_logs(self):
        self.ensure_one()
        return {
            'name': _('Execution Logs: %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'inter.company.log',
            'view_mode': 'list,form',
            'domain': [('rule_id', '=', self.id)],
            'context': {'default_rule_id': self.id},
        }


class InterCompanyLog(models.Model):
    _name = 'inter.company.log'
    _description = 'Inter-Company Transaction Audit Log'
    _order = 'create_date desc, id desc'

    rule_id = fields.Many2one('inter.company.rule', string='Triggered Rule', ondelete='cascade')
    name = fields.Char(string='Transaction Identifier', default=lambda self: _('Sync Transaction'))
    
    source_company_id = fields.Many2one('res.company', string='Originating Company', required=True)
    target_company_id = fields.Many2one('res.company', string='Recipient Company', required=True)

    source_doc_type = fields.Selection([
        ('purchase_order', 'Purchase Order'),
        ('sale_order', 'Sales Order'),
        ('invoice', 'Customer Invoice'),
        ('picking', 'Stock Delivery'),
    ], string='Source Document Type', required=True)
    source_doc_ref = fields.Char(string='Source Reference', required=True)

    target_doc_type = fields.Selection([
        ('purchase_order', 'Purchase Order'),
        ('sale_order', 'Sales Order'),
        ('invoice', 'Vendor Bill'),
        ('picking', 'Stock Receipt'),
    ], string='Mirrored Document Type', required=True)
    target_doc_ref = fields.Char(string='Mirrored Reference', default='Draft')

    amount = fields.Monetary(string='Synchronized Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    state = fields.Selection([
        ('success', 'Synchronized Successfully'),
        ('warning', 'Partial Sync / Warning'),
        ('error', 'Execution Failed'),
    ], string='Status', default='success', required=True)
    
    details = fields.Text(string='Execution Audit Trail')
