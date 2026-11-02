# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ApprovalMatrixRule(models.Model):
    _name = 'approval.matrix.rule'
    _description = 'Dynamic Multi-Level Approval Matrix Rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, min_amount desc, id'
    _check_company_auto = True

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    target_model = fields.Selection([
        ('sale_order', 'Sales Order'),
        ('purchase_order', 'Purchase Order'),
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
    ], string='Target Document', required=True, default='sale_order', tracking=True)

    amount_basis = fields.Selection([
        ('amount_untaxed', 'Untaxed Amount'),
        ('amount_total', 'Total Amount (Tax Incl.)'),
    ], string='Amount Evaluation Basis', default='amount_total', required=True)

    min_amount = fields.Monetary(
        string='Minimum Amount', currency_field='currency_id',
        default=0.0, required=True, tracking=True,
        help='Trigger this rule when the document amount is greater than or equal to this value.',
    )
    max_amount = fields.Monetary(
        string='Maximum Amount', currency_field='currency_id',
        default=0.0, tracking=True,
        help='Leave 0.0 for no upper limit.',
    )
    check_discount_limit = fields.Boolean(
        string='Trigger on Line Discount %',
        default=False,
        help='For Sales Orders: trigger approval even below Minimum Amount if any line discount exceeds Maximum Allowed Discount %.',
    )
    max_discount_percent = fields.Float(
        string='Max Allowed Line Discount (%)',
        default=10.0,
    )
    enforce_sequential = fields.Boolean(
        string='Sequential Multi-Tier Approval',
        default=True,
        help='Require lower sequence tiers to approve before notifying higher tiers.',
    )
    auto_confirm_on_approve = fields.Boolean(
        string='Auto-Confirm / Post on Final Approval',
        default=True,
        help='Automatically confirm the order or post the invoice once the final tier approves.',
    )
    line_ids = fields.One2many(
        'approval.matrix.rule.line', 'rule_id',
        string='Approval Tiers', copy=True,
    )

    @api.constrains('min_amount', 'max_amount')
    def _check_amount_range(self):
        for rule in self:
            if rule.min_amount < 0 or rule.max_amount < 0:
                raise ValidationError(_('Threshold amounts cannot be negative.'))
            if rule.max_amount > 0 and rule.max_amount < rule.min_amount:
                raise ValidationError(_('Maximum Amount must be greater than or equal to Minimum Amount.'))

    def _matches_document(self, amount_untaxed, amount_total, max_line_discount=0.0):
        self.ensure_one()
        eval_amount = amount_untaxed if self.amount_basis == 'amount_untaxed' else amount_total
        amount_match = eval_amount >= self.min_amount and (self.max_amount == 0.0 or eval_amount <= self.max_amount)
        discount_match = (
            self.target_model == 'sale_order'
            and self.check_discount_limit
            and max_line_discount > self.max_discount_percent
        )
        if self.min_amount > 0 and self.check_discount_limit:
            return amount_match or discount_match
        if self.check_discount_limit and self.min_amount == 0:
            return discount_match
        return amount_match

    @api.model
    def _find_matching_rule(self, target_model, company, amount_untaxed, amount_total, max_line_discount=0.0):
        rules = self.search([
            ('target_model', '=', target_model),
            ('company_id', '=', company.id),
            ('active', '=', True),
        ], order='sequence, min_amount desc, id')
        for rule in rules:
            if rule.line_ids and rule._matches_document(amount_untaxed, amount_total, max_line_discount):
                return rule
        return self.browse()


class ApprovalMatrixRuleLine(models.Model):
    _name = 'approval.matrix.rule.line'
    _description = 'Approval Matrix Tier Line'
    _order = 'sequence, id'
    _check_company_auto = True

    sequence = fields.Integer(string='Tier Sequence', default=10)
    rule_id = fields.Many2one(
        'approval.matrix.rule', string='Approval Rule',
        required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='rule_id.company_id', store=True)
    tier_name = fields.Char(string='Tier Name', required=True)
    approver_ids = fields.Many2many(
        'res.users',
        'approval_matrix_rule_line_res_users_rel',
        'line_id', 'user_id',
        string='Approvers', required=True,
        domain="[('share', '=', False)]",
    )
    minimum_approvals = fields.Integer(
        string='Min. Approvers Required', default=1, required=True,
    )

    @api.constrains('minimum_approvals', 'approver_ids')
    def _check_minimum_approvals(self):
        for line in self:
            if line.minimum_approvals < 1:
                raise ValidationError(_('Minimum Approvers Required must be at least 1.'))
            if line.approver_ids and line.minimum_approvals > len(line.approver_ids):
                raise ValidationError(
                    _('Minimum Approvers Required (%s) cannot exceed the number of assigned Approvers (%s) on tier "%s".')
                    % (line.minimum_approvals, len(line.approver_ids), line.tier_name)
                )


class ApprovalDocumentStep(models.Model):
    _name = 'approval.document.step'
    _description = 'Document Approval Tier Step'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    tier_name = fields.Char(string='Tier Name', required=True)
    rule_id = fields.Many2one('approval.matrix.rule', string='Matched Rule', ondelete='set null')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', index=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade', index=True)
    move_id = fields.Many2one('account.move', string='Journal Entry / Invoice', ondelete='cascade', index=True)

    approver_ids = fields.Many2many(
        'res.users',
        'approval_doc_step_approver_users_rel',
        'step_id', 'user_id',
        string='Eligible Approvers',
    )
    approved_user_ids = fields.Many2many(
        'res.users',
        'approval_doc_step_approved_users_rel',
        'step_id', 'user_id',
        string='Approved By',
    )
    minimum_approvals = fields.Integer(string='Required Approvals', default=1)
    status = fields.Selection([
        ('waiting', 'Waiting Previous Tier'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Tier Status', default='waiting', required=True)
    action_date = fields.Datetime(string='Last Decision Date', readonly=True)
    note = fields.Char(string='Decision Note', readonly=True)

    def action_open_source_document(self):
        self.ensure_one()
        doc = self.sale_order_id or self.purchase_order_id or self.move_id
        if not doc:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': doc._name,
            'res_id': doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

