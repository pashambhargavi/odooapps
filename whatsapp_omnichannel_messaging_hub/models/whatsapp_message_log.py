# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class WhatsAppMessageLog(models.Model):
    _name = 'whatsapp.message.log'
    _description = 'WhatsApp Message Audit Log'
    _order = 'id desc'

    name = fields.Char(string='Message Subject', required=True)
    recipient_name = fields.Char(string='Recipient Name')
    mobile_number = fields.Char(string='Recipient Mobile Number', required=True)
    body = fields.Text(string='Dispatched Message Body', required=True)
    res_model = fields.Char(string='Source Model', index=True)
    res_id = fields.Integer(string='Source Record ID', index=True)
    record_ref = fields.Char(string='Document Reference')
    user_id = fields.Many2one(
        'res.users', string='Dispatched By', default=lambda self: self.env.user,
    )
    date_sent = fields.Datetime(
        string='Sent Timestamp', default=fields.Datetime.now, required=True,
    )
    state = fields.Selection([
        ('sent', 'Dispatched via WhatsApp Web/App'),
        ('gateway_sent', 'Dispatched via Gateway API'),
        ('failed', 'Delivery Failed'),
    ], string='Status', default='sent', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
    )

    def action_open_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self.res_model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }
