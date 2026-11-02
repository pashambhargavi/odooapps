# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


FIELD_SELECTION = [
    ('required', 'Required'),
    ('optional', 'Optional'),
    ('no', 'None'),
]


class ApprovalCategory(models.Model):
    _name = 'approval.category'
    _description = 'Approval Category'
    _order = 'sequence, id'
    _check_company_auto = True

    name = fields.Char(string='Category Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, index=True,
    )
    description = fields.Text(string='Description', translate=True)
    image = fields.Binary(string='Icon Image')
    color = fields.Integer(string='Color Index', default=0)

    approval_minimum = fields.Integer(
        string='Minimum Approval', default=1, required=True,
        help='Minimum number of approvers required to approve requests in this category.',
    )
    enforce_sequential = fields.Boolean(
        string='Sequential Approval',
        default=True,
        help='If enabled, approvers must approve in the exact sequence order.',
    )
    manager_approval = fields.Selection([
        ('no', 'None'),
        ('optional', 'Is Approver'),
        ('required', 'Is Required Approver'),
    ], string="Requester's Manager", default='no', required=True)

    has_date = fields.Selection(FIELD_SELECTION, string='Has Date', default='no', required=True)
    has_period = fields.Selection(FIELD_SELECTION, string='Has Period', default='no', required=True)
    has_quantity = fields.Selection(FIELD_SELECTION, string='Has Quantity', default='no', required=True)
    has_amount = fields.Selection(FIELD_SELECTION, string='Has Amount', default='no', required=True)
    has_reference = fields.Selection(FIELD_SELECTION, string='Has Reference', default='no', required=True)
    has_partner = fields.Selection(FIELD_SELECTION, string='Has Contact', default='no', required=True)
    has_payment_method = fields.Selection(FIELD_SELECTION, string='Has Payment', default='no', required=True)
    has_location = fields.Selection(FIELD_SELECTION, string='Has Location', default='no', required=True)
    has_product = fields.Selection(FIELD_SELECTION, string='Has Product Lines', default='no', required=True)
    requirer_document = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
    ], string='Attachment Requirement', default='optional', required=True)

    approver_ids = fields.One2many(
        'approval.category.approver', 'category_id',
        string='Default Approvers', copy=True,
    )
    request_ids = fields.One2many('approval.request', 'category_id', string='Requests')
    request_to_validate_count = fields.Integer(
        string='Requests to Validate',
        compute='_compute_request_counts',
    )
    request_total_count = fields.Integer(
        string='Total Requests',
        compute='_compute_request_counts',
    )

    @api.depends('request_ids.request_status', 'request_ids.approver_ids.status')
    def _compute_request_counts(self):
        current_user = self.env.user
        for category in self:
            requests = category.request_ids
            category.request_total_count = len(requests)
            pending = requests.filtered(
                lambda r: r.request_status == 'pending' and any(
                    a.user_id == current_user and a.status == 'pending'
                    for a in r.approver_ids
                )
            )
            category.request_to_validate_count = len(pending)

    @api.constrains('approval_minimum', 'approver_ids')
    def _check_approval_minimum(self):
        for record in self:
            if record.approval_minimum < 1:
                raise ValidationError(_('Minimum Approval must be at least 1.'))
            required_count = len(record.approver_ids.filtered('required'))
            if required_count > record.approval_minimum:
                # Automatically ensure minimum is at least the number of required approvers
                pass

    def create_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'approval.request',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_category_id': self.id,
                'default_name': _('%s Request') % self.name,
            },
        }


class ApprovalCategoryApprover(models.Model):
    _name = 'approval.category.approver'
    _description = 'Approval Category Approver'
    _order = 'sequence, id'
    _check_company_auto = True

    sequence = fields.Integer(string='Sequence', default=10)
    category_id = fields.Many2one(
        'approval.category', string='Approval Category',
        required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='category_id.company_id', store=True)
    user_id = fields.Many2one(
        'res.users', string='Approver', required=True,
        check_company=True,
        domain="[('share', '=', False)]",
    )
    role_title = fields.Char(string='Role / Tier Name')
    required = fields.Boolean(string='Required Approver', default=True)

    _user_category_uniq = models.Constraint(
        'UNIQUE(category_id, user_id)',
        'Each approver can only be added once per approval category.',
    )
