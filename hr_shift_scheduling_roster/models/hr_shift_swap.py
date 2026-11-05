# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrShiftSwapRequest(models.Model):
    _name = 'hr.shift.swap.request'
    _description = 'Shift Swap and Trade Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='Request Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    requesting_employee_id = fields.Many2one('hr.employee', string='Requesting Colleague', required=True, tracking=True)
    original_shift_id = fields.Many2one('hr.shift.schedule', string='Shift to Relinquish', required=True, tracking=True)

    swap_type = fields.Selection([
        ('peer', 'Direct Trade with Specific Peer'),
        ('pool', 'Release to Open Shift Bidding Pool'),
    ], string='Trade Format', default='peer', required=True, tracking=True)

    target_employee_id = fields.Many2one('hr.employee', string='Proposed Exchange Peer', tracking=True)
    target_shift_id = fields.Many2one('hr.shift.schedule', string='Offered Peer Shift (Optional)', tracking=True)

    reason = fields.Text(string='Reason for Trade Request', required=True)
    manager_id = fields.Many2one('res.users', string='Approved By Manager', tracking=True)

    state = fields.Selection([
        ('draft', 'Requested'),
        ('peer_accepted', 'Peer Agreed'),
        ('manager_approved', 'Approved & Swapped'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.shift.swap.request') or _('New')
        return super().create(vals_list)

    def action_peer_accept(self):
        for record in self:
            if record.swap_type == 'peer' and not record.target_employee_id:
                raise UserError(_("Please designate a target colleague for direct peer trades."))
            record.write({'state': 'peer_accepted'})

    def action_manager_approve(self):
        for record in self:
            if record.swap_type == 'peer':
                if not record.target_employee_id:
                    raise UserError(_("Direct trade requires a target employee."))

                orig_emp = record.requesting_employee_id
                target_emp = record.target_employee_id

                # Assign original shift to target employee
                record.original_shift_id.write({
                    'employee_id': target_emp.id,
                    'state': 'swapped',
                })

                # If target shift provided, assign to original employee
                if record.target_shift_id:
                    record.target_shift_id.write({
                        'employee_id': orig_emp.id,
                        'state': 'swapped',
                    })
            else:
                # Release to open pool
                record.original_shift_id.write({
                    'employee_id': False,
                    'is_open_shift': True,
                    'state': 'draft',
                })

            record.write({
                'state': 'manager_approved',
                'manager_id': self.env.user.id,
            })

    def action_reject(self):
        for record in self:
            record.write({
                'state': 'rejected',
                'manager_id': self.env.user.id,
            })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancelled'})
