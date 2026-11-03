# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class HelpdeskTicketResolveWizard(models.TransientModel):
    _name = 'helpdesk.ticket.resolve.wizard'
    _description = 'Resolve Helpdesk Ticket Wizard'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True, readonly=True)
    resolution_summary = fields.Text(string='Resolution Notes / Root Cause', required=True)
    customer_rating = fields.Selection([
        ('0', 'Not Rated'),
        ('1', '1 - Very Dissatisfied'),
        ('2', '2 - Dissatisfied'),
        ('3', '3 - Neutral'),
        ('4', '4 - Satisfied'),
        ('5', '5 - Very Satisfied'),
    ], string='Customer Satisfaction Rating', default='5')

    def action_confirm_resolve(self):
        self.ensure_one()
        close_stage = self.env['helpdesk.stage'].search([('is_close', '=', True)], order='sequence, id', limit=1)
        now = fields.Datetime.now()
        vals = {
            'resolution_summary': self.resolution_summary,
            'closed_date': now,
        }
        if not self.ticket_id.first_response_date:
            vals['first_response_date'] = now
        if self.customer_rating and self.customer_rating != '0':
            vals['customer_rating'] = self.customer_rating
        if close_stage:
            vals['stage_id'] = close_stage.id
        self.ticket_id.write(vals)
        self.ticket_id.activity_feedback(['mail.mail_activity_data_todo', 'mail.mail_activity_data_warning'])
        self.ticket_id.message_post(
            body=_('Ticket resolved by <b>%s</b>.<br/><b>Resolution Summary:</b> %s') % (
                self.env.user.name,
                self.resolution_summary,
            ),
        )
        return {'type': 'ir.actions.act_window_close'}
