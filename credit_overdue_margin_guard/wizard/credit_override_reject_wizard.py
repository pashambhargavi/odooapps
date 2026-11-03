# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class CreditOverrideRejectWizard(models.TransientModel):
    _name = 'credit.override.reject.wizard'
    _description = 'Reject Credit / Margin Override Wizard'

    override_request_id = fields.Many2one(
        'credit.override.request', string='Override Request', required=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason', required=True,
    )

    def action_confirm_reject(self):
        self.ensure_one()
        if not self.rejection_reason or not self.rejection_reason.strip():
            raise UserError(_('Please provide a clear rejection reason.'))
        self.override_request_id._apply_rejection(self.rejection_reason.strip())
        return {'type': 'ir.actions.act_window_close'}
