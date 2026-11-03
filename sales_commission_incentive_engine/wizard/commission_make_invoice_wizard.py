# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CommissionMakeInvoiceWizard(models.TransientModel):
    _name = 'commission.make.invoice.wizard'
    _description = 'Generate Settlement Vendor Bill for Commission'

    def _default_partner_id(self):
        ws_id = self.env.context.get('active_id')
        if ws_id:
            ws = self.env['commission.worksheet'].browse(ws_id)
            if ws.agent_partner_id:
                return ws.agent_partner_id
            if ws.salesperson_id and ws.salesperson_id.partner_id:
                return ws.salesperson_id.partner_id
        return False

    def _default_journal_id(self):
        return self.env['account.journal'].search([
            ('type', '=', 'purchase'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

    worksheet_id = fields.Many2one(
        'commission.worksheet', string='Commission Worksheet', required=True,
        default=lambda self: self.env.context.get('active_id'),
    )
    partner_id = fields.Many2one(
        'res.partner', string='Vendor / Beneficiary Contact', required=True,
        default=_default_partner_id,
    )
    journal_id = fields.Many2one(
        'account.journal', string='Purchase Journal', required=True,
        default=_default_journal_id,
        domain="[('type', '=', 'purchase')]",
    )
    invoice_date = fields.Date(
        string='Bill Date', required=True, default=fields.Date.context_today,
    )
    commission_amount = fields.Monetary(
        string='Settlement Amount', related='worksheet_id.total_commission_amount',
        currency_field='currency_id', readonly=True,
    )
    currency_id = fields.Many2one(
        related='worksheet_id.currency_id', readonly=True,
    )

    def action_create_vendor_bill(self):
        self.ensure_one()
        ws = self.worksheet_id
        if ws.state != 'approved':
            raise UserError(_('You can only generate a Vendor Bill for approved commission worksheets.'))
        if ws.vendor_bill_id and ws.vendor_bill_id.state != 'cancel':
            raise UserError(_('A Vendor Bill (%s) already exists for this worksheet.') % ws.vendor_bill_id.name)

        bill_vals = {
            'move_type': 'in_invoice',
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'invoice_date': self.invoice_date,
            'date': self.invoice_date,
            'company_id': ws.company_id.id,
            'ref': _('Commission Settlement: %s') % ws.name,
            'invoice_line_ids': [(0, 0, {
                'name': _('Sales Commission Settlement (%s to %s) - %s') % (ws.date_start, ws.date_end, ws.name),
                'quantity': 1.0,
                'price_unit': ws.total_commission_amount,
            })],
        }
        bill = self.env['account.move'].create(bill_vals)
        ws.write({
            'vendor_bill_id': bill.id,
            'state': 'settled',
        })
        ws.line_ids.write({'state': 'paid'})
        ws.message_post(
            body=_('Generated Vendor Bill <b>%s</b> for commission settlement.') % bill.name,
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Settlement Vendor Bill'),
            'res_model': 'account.move',
            'res_id': bill.id,
            'view_mode': 'form',
            'target': 'current',
        }
