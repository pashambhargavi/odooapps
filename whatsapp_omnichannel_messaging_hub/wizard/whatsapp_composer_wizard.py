# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
import urllib.parse
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WhatsAppComposerWizard(models.TransientModel):
    _name = 'whatsapp.composer.wizard'
    _description = 'Interactive WhatsApp Message Composer'

    partner_id = fields.Many2one(
        'res.partner', string='Recipient Customer', required=True,
    )
    mobile_number = fields.Char(
        string='Mobile Number (with country code)', required=True,
        help='Include international country code without plus sign (e.g. 15551234567 or 919876543210).'
    )
    template_id = fields.Many2one(
        'whatsapp.template', string='Message Template',
    )
    message_body = fields.Text(
        string='Message Preview & Edit', required=True,
    )
    res_model = fields.Char(string='Source Model')
    res_id = fields.Integer(string='Source Record ID')
    record_ref = fields.Char(string='Document Reference')

    @api.onchange('template_id')
    def _onchange_template_id(self):
        if self.template_id and self.res_model and self.res_id:
            record = self.env[self.res_model].browse(self.res_id)
            if record.exists():
                self.message_body = self.template_id.render_template(record)

    def _clean_phone_number(self, phone):
        """Sanitizes raw phone input to clean digits for WhatsApp URL format."""
        if not phone:
            return ""
        clean = re.sub(r'[^0-9]', '', str(phone))
        # Strip leading zeros if present
        clean = clean.lstrip('0')
        return clean

    def action_send_whatsapp(self):
        self.ensure_one()
        phone_digits = self._clean_phone_number(self.mobile_number)
        if not phone_digits or len(phone_digits) < 7:
            raise UserError(_('Please enter a valid mobile number with country code (e.g. 15551234567 or 919876543210).'))

        # 1. Create audit log
        self.env['whatsapp.message.log'].create({
            'name': _('WhatsApp: %s') % (self.record_ref or self.partner_id.name),
            'recipient_name': self.partner_id.name,
            'mobile_number': phone_digits,
            'body': self.message_body,
            'res_model': self.res_model,
            'res_id': self.res_id,
            'record_ref': self.record_ref,
            'user_id': self.env.user.id,
            'state': 'sent',
            'company_id': self.env.company.id,
        })

        # 2. Log chatter activity on source document
        if self.res_model and self.res_id:
            record = self.env[self.res_model].browse(self.res_id)
            if record.exists() and hasattr(record, 'message_post'):
                record.message_post(
                    body=_(
                        '<b>WhatsApp Message Dispatched</b> to <b>%s</b> (+%s):<br/>'
                        '<blockquote style="border-left: 3px solid #25D366; padding-left: 8px; margin: 4px 0; color: #475569;">'
                        '%s'
                        '</blockquote>'
                    ) % (
                        self.partner_id.name, phone_digits, self.message_body.replace('\n', '<br/>')
                    ),
                    subject=_('WhatsApp Sent to %s') % self.partner_id.name,
                )

        # 3. Generate direct WhatsApp Web / Mobile redirect URL
        encoded_text = urllib.parse.quote(self.message_body)
        whatsapp_url = f"https://api.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"

        return {
            'type': 'ir.actions.act_url',
            'url': whatsapp_url,
            'target': 'new',
        }
