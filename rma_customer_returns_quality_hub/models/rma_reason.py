# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class RmaReason(models.Model):
    _name = 'rma.reason'
    _description = 'RMA Return Reason'
    _order = 'sequence, name'

    name = fields.Char(string='Reason', required=True, translate=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    default_action = fields.Selection([
        ('refund', 'Refund / Credit Note'),
        ('replacement', 'Replacement Delivery'),
        ('repair', 'Repair & Return'),
        ('scrap', 'Scrap & Write-Off'),
    ], string='Default Recommended Action', default='refund')
    description = fields.Text(string='Internal Notes')
