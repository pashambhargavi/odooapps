# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class ApprovalRejectWizard(models.TransientModel):
    _name = 'approval.reject.wizard'
    _description = 'Approval Rejection Reason Wizard'

    res_model = fields.Char(string='Target Model', required=True, readonly=True)
    res_id = fields.Integer(string='Target Record ID', required=True, readonly=True)
    reason = fields.Text(string='Rejection Reason', required=True)

    def action_confirm_reject(self):
        self.ensure_one()
        allowed_models = {'approval.request', 'sale.order', 'purchase.order', 'account.move'}
        if self.res_model not in allowed_models:
            raise UserError(_('Unsupported document model for rejection.'))
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_('The target document no longer exists.'))
        record._apply_rejection(self.reason)
        return {'type': 'ir.actions.act_window_close'}
