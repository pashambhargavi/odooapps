# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    whatsapp_log_count = fields.Integer(
        string='WhatsApp Messages Count', compute='_compute_whatsapp_log_count',
    )

    def _compute_whatsapp_log_count(self):
        for picking in self:
            picking.whatsapp_log_count = self.env['whatsapp.message.log'].search_count([
                ('res_model', '=', 'stock.picking'),
                ('res_id', '=', picking.id),
            ])

    def action_send_whatsapp(self):
        self.ensure_one()
        phone = getattr(self.partner_id, 'mobile', False) or self.partner_id.phone
        if not phone:
            raise UserError(_('Partner %s does not have a Phone or Mobile number.') % self.partner_id.name)

        template = self.env['whatsapp.template'].search([
            ('model', '=', 'stock.picking'),
            ('company_id', 'in', [self.company_id.id, False]),
        ], limit=1)

        body = template.render_template(self) if template else _(
            'Hello %s, your delivery order %s has been processed and dispatched from %s.'
        ) % (
            self.partner_id.name, self.name, self.company_id.name
        )

        return {
            'name': _('Send WhatsApp Delivery Notice'),
            'type': 'ir.actions.act_window',
            'res_model': 'whatsapp.composer.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.partner_id.id,
                'default_mobile_number': phone,
                'default_template_id': template.id if template else False,
                'default_message_body': body,
                'default_res_model': 'stock.picking',
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
            'domain': [('res_model', '=', 'stock.picking'), ('res_id', '=', self.id)],
            'context': {'default_res_model': 'stock.picking', 'default_res_id': self.id},
        }
