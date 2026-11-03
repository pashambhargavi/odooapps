# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class CommissionWorksheet(models.Model):
    _name = 'commission.worksheet'
    _description = 'Sales Commission Settlement Worksheet'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'
    _check_company_auto = True

    name = fields.Char(
        string='Worksheet Reference', required=True, copy=False,
        readonly=True, default=lambda self: _('New'), index=True,
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    beneficiary_type = fields.Selection([
        ('salesperson', 'Internal Sales Representative'),
        ('manager', 'Sales Manager / Team Leader'),
        ('partner', 'External Partner / Referral Agent'),
    ], string='Beneficiary Type', default='salesperson', required=True, tracking=True)

    salesperson_id = fields.Many2one(
        'res.users', string='Sales Representative / Manager',
        tracking=True, index=True,
    )
    agent_partner_id = fields.Many2one(
        'res.partner', string='Partner / Agent Contact',
        tracking=True, index=True,
    )

    date_start = fields.Date(string='Period Start', required=True, tracking=True)
    date_end = fields.Date(string='Period End', required=True, tracking=True)
    date_approved = fields.Datetime(string='Approved On', readonly=True, tracking=True)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, tracking=True)

    line_ids = fields.One2many(
        'commission.line', 'worksheet_id', string='Commission Lines',
    )
    total_base_amount = fields.Monetary(
        string='Total Sales Volume', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    total_commission_amount = fields.Monetary(
        string='Net Payable Commission', currency_field='currency_id',
        compute='_compute_totals', store=True,
    )
    lines_count = fields.Integer(
        string='Commission Lines Count', compute='_compute_totals', store=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('calculated', 'Calculated'),
        ('approved', 'Approved'),
        ('settled', 'Settled / Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True, index=True)

    vendor_bill_id = fields.Many2one(
        'account.move', string='Settlement Vendor Bill',
        readonly=True, copy=False, tracking=True,
    )
    notes = fields.Text(string='Notes & Settlement Details')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('commission.worksheet') or _('New')
        return super().create(vals_list)

    @api.depends('line_ids.base_amount', 'line_ids.commission_amount')
    def _compute_totals(self):
        for ws in self:
            ws.total_base_amount = sum(ws.line_ids.mapped('base_amount'))
            ws.total_commission_amount = sum(ws.line_ids.mapped('commission_amount'))
            ws.lines_count = len(ws.line_ids)

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for ws in self:
            if ws.date_start and ws.date_end and ws.date_start > ws.date_end:
                raise ValidationError(_('Period Start date cannot be after Period End date.'))

    def action_calculate_commissions(self):
        """Find matching unassigned commission lines in the date range and attach to this worksheet."""
        for ws in self:
            domain = [
                ('company_id', '=', ws.company_id.id),
                ('worksheet_id', '=', False),
                ('state', 'in', ('draft', 'approved')),
                ('date', '>=', ws.date_start),
                ('date', '<=', ws.date_end),
            ]
            if ws.beneficiary_type in ('salesperson', 'manager') and ws.salesperson_id:
                domain.append(('salesperson_id', '=', ws.salesperson_id.id))
                domain.append(('beneficiary_type', '=', ws.beneficiary_type))
            elif ws.beneficiary_type == 'partner' and ws.agent_partner_id:
                domain.append(('agent_partner_id', '=', ws.agent_partner_id.id))

            unassigned_lines = self.env['commission.line'].search(domain)
            if not unassigned_lines:
                raise UserError(_('No unassigned commission lines found for the specified person and period.'))

            unassigned_lines.write({'worksheet_id': ws.id})
            ws.write({'state': 'calculated'})
            ws.message_post(
                body=_('Worksheet calculated: Attached <b>%s</b> commission lines totaling <b>%s</b>.') % (
                    len(unassigned_lines), ws.total_commission_amount,
                ),
            )
        return True

    def action_approve(self):
        for ws in self:
            if not ws.line_ids:
                raise UserError(_('Cannot approve an empty commission worksheet.'))
            ws.write({
                'state': 'approved',
                'approved_by_id': self.env.user.id,
                'date_approved': fields.Datetime.now(),
            })
            ws.line_ids.write({'state': 'approved'})
            ws.message_post(
                body=_('Commission Worksheet <b>%s</b> approved by <b>%s</b>.') % (ws.name, self.env.user.name),
            )
        return True

    def action_mark_settled(self):
        for ws in self:
            ws.write({'state': 'settled'})
            ws.line_ids.write({'state': 'paid'})
            ws.message_post(body=_('Commission worksheet marked as fully Settled / Paid.'))
        return True

    def action_reset_to_draft(self):
        for ws in self:
            if ws.vendor_bill_id and ws.vendor_bill_id.state != 'cancel':
                raise UserError(_('Please cancel the linked Vendor Bill before resetting this worksheet.'))
            ws.line_ids.write({'state': 'draft'})
            ws.write({
                'state': 'draft',
                'approved_by_id': False,
                'date_approved': False,
            })
        return True

    def action_open_vendor_bill(self):
        self.ensure_one()
        if not self.vendor_bill_id:
            raise UserError(_('No Vendor Bill has been generated for this worksheet.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Vendor Bill'),
            'res_model': 'account.move',
            'res_id': self.vendor_bill_id.id,
            'view_mode': 'form',
        }


class CommissionLine(models.Model):
    _name = 'commission.line'
    _description = 'Individual Commission Ledger Line'
    _order = 'date desc, id desc'
    _check_company_auto = True

    name = fields.Char(string='Description', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, required=True, index=True,
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='company_id.currency_id', store=True, readonly=True,
    )
    plan_id = fields.Many2one('commission.plan', string='Applied Plan', index=True)

    beneficiary_type = fields.Selection([
        ('salesperson', 'Direct Salesperson'),
        ('manager', 'Manager Override'),
        ('partner', 'External Partner / Agent'),
    ], string='Role', default='salesperson', required=True)

    salesperson_id = fields.Many2one('res.users', string='Sales Rep / Manager', index=True)
    agent_partner_id = fields.Many2one('res.partner', string='Agent Partner', index=True)

    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', index=True)
    invoice_id = fields.Many2one('account.move', string='Customer Invoice', ondelete='set null', index=True)
    partner_id = fields.Many2one('res.partner', string='Customer', index=True)
    product_id = fields.Many2one('product.product', string='Product')

    base_amount = fields.Monetary(
        string='Sales Base Amount', required=True, currency_field='currency_id',
    )
    margin_amount = fields.Monetary(
        string='Gross Margin Amount', currency_field='currency_id', default=0.0,
    )
    rate = fields.Float(string='Commission Rate (%)', required=True, default=0.0)
    commission_amount = fields.Monetary(
        string='Commission Earned', required=True, currency_field='currency_id',
    )

    worksheet_id = fields.Many2one(
        'commission.worksheet', string='Settlement Worksheet', ondelete='set null', index=True,
    )
    state = fields.Selection([
        ('draft', 'Accrued (Draft)'),
        ('approved', 'Verified & Approved'),
        ('paid', 'Settled / Paid'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True)
