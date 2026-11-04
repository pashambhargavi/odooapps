# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    whatsapp_log_count = fields.Integer(
        string='WhatsApp Messages Count', compute='_compute_whatsapp_log_count',
    )

    def _compute_whatsapp_log_count(self):
        for move in self:
            move.whatsapp_log_count = self.env['whatsapp.message.log'].search_count([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
            ])

    def action_send_whatsapp(self):
        self.ensure_one()
        phone = getattr(self.partner_id, 'mobile', False) or self.partner_id.phone
        if not phone:
            raise UserError(_('Customer %s does not have a Phone or Mobile number.') % self.partner_id.name)

        template = self.env['whatsapp.template'].search([
            ('model', '=', 'account.move'),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)

        body = template.render_template(self) if template else _(
            'Hello %s, please find your Invoice %s for %s %s due on %s from %s.'
        ) % (
            self.partner_id.name, self.name, self.currency_id.symbol or '', self.amount_total, self.invoice_date_due or '', self.company_id.name
        )

        return {
            'name': _('Send WhatsApp Message'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.composer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_mobile_number': phone,
                'default_template_id': template.id if template else False,
                'default_message_body': body,
                'default_res_model': 'account.move',
                'default_res_id': self.id,
                'default_record_ref': self.name,
            },
        }

    def action_view_whatsapp_logs(self):
        self.ensure_one()
        return {
            'name': _('WhatsApp Logs - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.message.log',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', 'account.move'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'account.move', 'default_res_id': self.id},
        }
