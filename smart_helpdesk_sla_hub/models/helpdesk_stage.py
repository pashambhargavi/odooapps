# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HelpdeskStage(models.Model):
    _name = 'helpdesk.stage'
    _description = 'Helpdesk Ticket Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    fold = fields.Boolean(string='Folded in Kanban', default=False)
    is_in_progress = fields.Boolean(
        string='Marks First Response',
        default=False,
        help='Moving a ticket to this stage automatically records the First Response Date.',
    )
    is_close = fields.Boolean(
        string='Closing Stage',
        default=False,
        help='Tickets in this stage are considered Solved / Closed for SLA evaluation.',
    )
    is_cancel = fields.Boolean(
        string='Canceled Stage',
        default=False,
        help='Tickets in this stage are considered Canceled.',
    )
    description = fields.Text(string='Stage Description', translate=True)


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'
    _order = 'sequence, name'

    name = fields.Char(string='Type Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    code = fields.Char(string='Code')


class HelpdeskTag(models.Model):
    _name = 'helpdesk.tag'
    _description = 'Helpdesk Tag'
    _order = 'name'

    name = fields.Char(string='Tag Name', required=True, translate=True)
    color = fields.Integer(string='Color Index', default=1)

    _tag_name_uniq = models.Constraint(
        'UNIQUE(name)',
        'Tag name must be unique.',
    )
