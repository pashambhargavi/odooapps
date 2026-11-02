# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command


class ApprovalRequest(models.Model):
    _name = 'approval.request'
    _description = 'Approval Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Request Subject', required=True, tracking=True)
    reference_code = fields.Char(
        string='Request Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'), index=True,
    )
    category_id = fields.Many2one(
        'approval.category', string='Category',
        required=True, tracking=True, check_company=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    request_owner_id = fields.Many2one(
        'res.users', string='Request Owner',
        default=lambda self: self.env.user, required=True,
        tracking=True, check_company=True,
    )
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='0', tracking=True)

    date = fields.Date(string='Date', tracking=True)
    date_start = fields.Datetime(string='Start Period', tracking=True)
    date_end = fields.Datetime(string='End Period', tracking=True)
    quantity = fields.Float(string='Quantity', tracking=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id', tracking=True)
    reference = fields.Char(string='External Reference', tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Contact / Vendor',
        check_company=True, tracking=True,
    )
    location = fields.Char(string='Location / Destination', tracking=True)
    reason = fields.Html(string='Description / Business Justification')
    rejection_reason = fields.Text(string='Last Rejection Reason', readonly=True, tracking=True)

    date_confirmed = fields.Datetime(string='Submitted On', readonly=True, copy=False, tracking=True)
    date_approved = fields.Datetime(string='Approved On', readonly=True, copy=False, tracking=True)

    # Category field visibility flags
    has_date = fields.Selection(related='category_id.has_date')
    has_period = fields.Selection(related='category_id.has_period')
    has_quantity = fields.Selection(related='category_id.has_quantity')
    has_amount = fields.Selection(related='category_id.has_amount')
    has_reference = fields.Selection(related='category_id.has_reference')
    has_partner = fields.Selection(related='category_id.has_partner')
    has_payment_method = fields.Selection(related='category_id.has_payment_method')
    has_location = fields.Selection(related='category_id.has_location')
    has_product = fields.Selection(related='category_id.has_product')
    requirer_document = fields.Selection(related='category_id.requirer_document')
    approval_minimum = fields.Integer(related='category_id.approval_minimum')
    enforce_sequential = fields.Boolean(related='category_id.enforce_sequential')

    approver_ids = fields.One2many(
        'approval.request.approver', 'request_id',
        string='Approvers', copy=False,
    )
    line_ids = fields.One2many(
        'approval.request.line', 'request_id',
        string='Product Lines', copy=True,
    )

    request_status = fields.Selection([
        ('new', 'To Submit'),
        ('pending', 'Submitted'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
    ], string='Status', default='new', compute='_compute_request_status',
       store=True, tracking=True, group_expand='_read_group_request_status')

    user_status = fields.Selection([
        ('new', 'New'),
        ('pending', 'To Approve'),
        ('waiting', 'Waiting Previous Tier'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
    ], string='My Approval Status', compute='_compute_user_status')

    is_current_approver = fields.Boolean(
        string='Is Current Approver',
        compute='_compute_user_status',
    )
    attachment_number = fields.Integer(
        string='Number of Attachments',
        compute='_compute_attachment_number',
    )

    @api.model
    def _read_group_request_status(self, stages, domain):
        return [key for key, _val in self._fields['request_status'].selection]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference_code', _('New')) == _('New'):
                vals['reference_code'] = self.env['ir.sequence'].next_by_code('approval.request') or _('New')
        records = super().create(vals_list)
        for record in records:
            if not record.approver_ids and record.category_id:
                record._sync_category_approvers()
        return records

    @api.onchange('category_id')
    def _onchange_category_id(self):
        if self.category_id:
            self._sync_category_approvers()

    def _sync_category_approvers(self):
        for request in self:
            commands = [Command.clear()]
            for cat_approver in request.category_id.approver_ids.sorted('sequence'):
                commands.append(Command.create({
                    'sequence': cat_approver.sequence,
                    'user_id': cat_approver.user_id.id,
                    'role_title': cat_approver.role_title or _('Approver'),
                    'required': cat_approver.required,
                    'status': 'new',
                }))
            request.approver_ids = commands

    def _compute_attachment_number(self):
        domain = [('res_model', '=', 'approval.request'), ('res_id', 'in', self.ids)]
        attachment_data = self.env['ir.attachment']._read_group(domain, ['res_id'], ['__count'])
        mapped_data = dict(attachment_data)
        for request in self:
            request.attachment_number = mapped_data.get(request.id, 0)

    def action_get_attachment_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Attachments'),
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('res_model', '=', 'approval.request'), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': 'approval.request',
                'default_res_id': self.id,
            },
        }

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.approver_ids.mapped('status')
            required_approvers = request.approver_ids.filtered('required')
            required_statuses = required_approvers.mapped('status')
            minimal_approver = request.approval_minimum if len(status_lst) >= request.approval_minimum else len(status_lst)

            if not status_lst:
                request.request_status = 'new'
            elif status_lst.count('cancel'):
                request.request_status = 'cancel'
            elif status_lst.count('refused'):
                request.request_status = 'refused'
            elif status_lst.count('new') == len(status_lst):
                request.request_status = 'new'
            elif (
                status_lst.count('approved') >= minimal_approver
                and (not required_statuses or all(s == 'approved' for s in required_statuses))
            ):
                request.request_status = 'approved'
            else:
                request.request_status = 'pending'

    @api.depends('approver_ids.status', 'approver_ids.user_id', 'request_status')
    def _compute_user_status(self):
        current_user = self.env.user
        for request in self:
            user_approver = request.approver_ids.filtered(lambda a: a.user_id == current_user)[:1]
            request.user_status = user_approver.status if user_approver else False
            request.is_current_approver = bool(
                request.request_status == 'pending'
                and user_approver
                and user_approver.status == 'pending'
            )

    @api.constrains('date_start', 'date_end')
    def _check_period_dates(self):
        for request in self:
            if request.date_start and request.date_end and request.date_start > request.date_end:
                raise ValidationError(_('Start Period cannot be later than End Period.'))

    def action_confirm(self):
        for request in self:
            if not request.approver_ids and request.category_id:
                request._sync_category_approvers()
            if not request.approver_ids:
                raise UserError(_('Please configure at least one approver before submitting this request.'))
            if request.requirer_document == 'required' and request.attachment_number == 0:
                raise UserError(_('You must attach at least one supporting document before submitting.'))
            if request.has_product == 'required' and not request.line_ids:
                raise UserError(_('Please add at least one product line before submitting.'))

            sorted_approvers = request.approver_ids.sorted('sequence')
            if request.enforce_sequential:
                first_seq = sorted_approvers[0].sequence
                for approver in sorted_approvers:
                    if approver.sequence == first_seq:
                        approver.status = 'pending'
                        approver._create_activity()
                    else:
                        approver.status = 'waiting'
            else:
                for approver in sorted_approvers:
                    approver.status = 'pending'
                    approver._create_activity()

            request.write({
                'date_confirmed': fields.Datetime.now(),
                'rejection_reason': False,
            })
            request.message_post(
                body=_('Approval request <b>%s</b> submitted by %s.') % (request.reference_code, self.env.user.name),
            )
        return True

    def action_approve(self, approver=None):
        for request in self:
            if not isinstance(approver, models.BaseModel):
                approver = request.approver_ids.filtered(
                    lambda a: a.user_id == self.env.user and a.status == 'pending'
                )[:1]
            if not approver and self.env.user.has_group('dynamic_approval_governance.group_approval_manager'):
                approver = request.approver_ids.filtered(lambda a: a.status == 'pending')[:1]
            if not approver:
                raise UserError(_('You do not have a pending approval step on this request.'))

            approver.write({
                'status': 'approved',
                'action_date': fields.Datetime.now(),
            })
            request.activity_feedback(['mail.mail_activity_data_todo'], user_id=approver.user_id.id)
            request.message_post(
                body=_('Tier <b>%s</b> approved by <b>%s</b>.') % (
                    approver.role_title or _('Approver'),
                    self.env.user.name,
                ),
            )

            # Activate next sequential tier if applicable
            if request.enforce_sequential and not request.approver_ids.filtered(lambda a: a.status == 'pending'):
                waiting_approvers = request.approver_ids.filtered(lambda a: a.status == 'waiting').sorted('sequence')
                if waiting_approvers:
                    next_seq = waiting_approvers[0].sequence
                    for next_app in waiting_approvers.filtered(lambda a: a.sequence == next_seq):
                        next_app.status = 'pending'
                        next_app._create_activity()

            request._compute_request_status()
            if request.request_status == 'approved':
                request.date_approved = fields.Datetime.now()
                # Clear any remaining waiting/pending optional approvers
                request.approver_ids.filtered(lambda a: a.status in ('waiting', 'pending')).write({'status': 'new'})
                request.message_post(
                    body=_('Request <b>%s</b> has been fully <b>Approved</b>.') % request.reference_code,
                )
        return True

    def action_open_reject_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refuse Approval Request'),
            'res_model': 'approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': 'approval.request',
                'default_res_id': self.id,
            },
        }

    def _apply_rejection(self, reason):
        for request in self:
            approver = request.approver_ids.filtered(
                lambda a: a.user_id == self.env.user and a.status in ('pending', 'approved')
            )[:1]
            if not approver and self.env.user.has_group('dynamic_approval_governance.group_approval_manager'):
                approver = request.approver_ids.filtered(lambda a: a.status in ('pending', 'waiting'))[:1]
            if not approver:
                raise UserError(_('You are not authorized to refuse this request.'))

            approver.write({
                'status': 'refused',
                'action_date': fields.Datetime.now(),
                'note': reason,
            })
            request.rejection_reason = reason
            request.activity_unlink(['mail.mail_activity_data_todo'])
            request.message_post(
                body=_('Request refused by <b>%s</b>.<br/><b>Reason:</b> %s') % (self.env.user.name, reason),
            )

    def action_withdraw(self):
        for request in self:
            request.approver_ids.write({
                'status': 'new',
                'action_date': False,
                'note': False,
            })
            request.write({
                'date_confirmed': False,
                'date_approved': False,
            })
            request.activity_unlink(['mail.mail_activity_data_todo'])
            request.message_post(body=_('Request reset to draft by %s.') % self.env.user.name)
        return True

    def action_cancel(self):
        for request in self:
            request.approver_ids.write({'status': 'cancel'})
            request.activity_unlink(['mail.mail_activity_data_todo'])
            request.message_post(body=_('Request canceled by %s.') % self.env.user.name)
        return True


class ApprovalRequestApprover(models.Model):
    _name = 'approval.request.approver'
    _description = 'Approval Request Approver'
    _order = 'sequence, id'
    _check_company_auto = True

    sequence = fields.Integer(string='Sequence', default=10)
    request_id = fields.Many2one(
        'approval.request', string='Request',
        required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='request_id.company_id', store=True)
    user_id = fields.Many2one(
        'res.users', string='Approver', required=True,
        check_company=True, domain="[('share', '=', False)]",
    )
    role_title = fields.Char(string='Role / Tier', default='Approver')
    required = fields.Boolean(string='Required', default=True)
    status = fields.Selection([
        ('new', 'New'),
        ('waiting', 'Waiting Previous Tier'),
        ('pending', 'To Approve'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancel', 'Canceled'),
    ], string='Status', default='new', readonly=True)
    action_date = fields.Datetime(string='Decision Date', readonly=True)
    note = fields.Char(string='Decision Note', readonly=True)

    def _create_activity(self):
        for approver in self:
            approver.request_id.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=approver.user_id.id,
                summary=_('Approval Required: %s') % approver.request_id.name,
                note=_('Please review and approve request %s (%s).') % (
                    approver.request_id.reference_code,
                    approver.request_id.category_id.name,
                ),
            )


class ApprovalRequestLine(models.Model):
    _name = 'approval.request.line'
    _description = 'Approval Request Product Line'
    _check_company_auto = True

    request_id = fields.Many2one(
        'approval.request', string='Approval Request',
        required=True, ondelete='cascade',
    )
    company_id = fields.Many2one(related='request_id.company_id', store=True)
    currency_id = fields.Many2one(related='request_id.currency_id')
    product_id = fields.Many2one(
        'product.product', string='Product',
        required=True, check_company=True,
    )
    description = fields.Char(
        string='Description', required=True,
        compute='_compute_description', store=True, readonly=False,
    )
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', string='Unit of Measure',
        compute='_compute_product_uom_id', store=True, readonly=False,
    )
    price_unit = fields.Monetary(
        string='Estimated Unit Price',
        currency_field='currency_id',
        compute='_compute_price_unit', store=True, readonly=False,
    )
    price_subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_price_subtotal', store=True,
    )

    @api.depends('product_id')
    def _compute_description(self):
        for line in self:
            if line.product_id and not line.description:
                line.description = line.product_id.display_name

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for line in self:
            if line.product_id:
                line.product_uom_id = line.product_id.uom_id

    @api.depends('product_id')
    def _compute_price_unit(self):
        for line in self:
            if line.product_id and not line.price_unit:
                line.price_unit = line.product_id.standard_price or line.product_id.lst_price

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit
