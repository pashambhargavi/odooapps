# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    whatsapp_log_count = fields.Integer(
        string='WhatsApp Messages Count', compute='_compute_whatsapp_log_count',
    )

    def _compute_whatsapp_log_count(self):
        for partner in self:
            partner.whatsapp_log_count = self.env['whatsapp.message.log'].search_count([
                ('res_model', '=', 'res.partner'),
                ('res_id', '=', partner.id),
            ])

    def action_send_whatsapp(self):
        self.ensure_one()
        phone = getattr(self, 'mobile', False) or self.phone
        if not phone:
            raise UserError(_('Partner %s does not have a Phone or Mobile number.') % self.name)

        template = self.env['whatsapp.template'].search([
            ('model', '=', 'res.partner'),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)

        body = template.render_template(self) if template else _(
            'Hello %s, greetings from %s!'
        ) % (
            self.name, self.company_id.name if self.company_id else self.env.company.name
        )

        return {
            'name': _('Chat via WhatsApp'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.composer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_mobile_number': phone,
                'default_template_id': template.id if template else False,
                'default_message_body': body,
                'default_res_model': 'res.partner',
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
            'domain': [('res_model', '=', 'res.partner'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'res.partner', 'default_res_id': self.id},
        }
