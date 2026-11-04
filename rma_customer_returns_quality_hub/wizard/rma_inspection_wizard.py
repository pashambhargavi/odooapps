# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class RmaInspectionWizard(models.TransientModel):
    _name = 'rma.inspection.wizard'
    _description = 'RMA Quality Inspection Workbench'

    rma_id = fields.Many2one('rma.order', string='RMA Reference', required=True, readonly=True)
    line_ids = fields.One2many('rma.inspection.wizard.line', 'wizard_id', string='Inspection Lines')
    global_disposition = fields.Selection([
        ('refund', 'Generate Customer Refund (Credit Note)'),
        ('replacement', 'Dispatch Free Replacement Order'),
        ('repair', 'Route to Internal Repair'),
        ('scrap', 'Scrap Without Refund'),
    ], string='Final Operational Decision', default='refund', required=True)
    internal_notes = fields.Text(string='Inspection Summary & Findings')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        rma_id = self.env.context.get('default_rma_id') or self.env.context.get('active_id')
        if rma_id:
            rma = self.env['rma.order'].browse(rma_id)
            res['rma_id'] = rma.id
            res['global_disposition'] = rma.resolution_type or 'refund'
            lines = []
            for line in rma.line_ids:
                lines.append((0, 0, {
                    'rma_line_id': line.id,
                    'product_id': line.product_id.id,
                    'return_qty': line.return_qty,
                    'inspected_qty': line.return_qty,
                    'inspection_state': 'passed',
                }))
            res['line_ids'] = lines
        return res

    def action_apply_inspection(self):
        self.ensure_one()
        rma = self.rma_id
        for wline in self.line_ids:
            if wline.rma_line_id:
                wline.rma_line_id.write({
                    'inspection_state': wline.inspection_state,
                    'inspected_qty': wline.inspected_qty,
                    'inspection_notes': wline.notes,
                })

        rma.resolution_type = self.global_disposition
        rma.state = 'inspected'
        rma.message_post(body=_(
            'Quality Inspection Completed.<br/>Decision: <b>%s</b>.<br/>Findings: %s'
        ) % (dict(self._fields['global_disposition'].selection).get(self.global_disposition), self.internal_notes or 'None'))

        if self.global_disposition == 'refund':
            return rma.action_create_credit_note()
        elif self.global_disposition == 'replacement':
            return rma.action_create_replacement_delivery()
        elif self.global_disposition in ('repair', 'scrap'):
            rma.action_resolve()
            return {'type': 'ir.actions.act_window_close'}
        return {'type': 'ir.actions.act_window_close'}


class RmaInspectionWizardLine(models.TransientModel):
    _name = 'rma.inspection.wizard.line'
    _description = 'RMA Quality Inspection Line'

    wizard_id = fields.Many2one('rma.inspection.wizard', required=True, ondelete='cascade')
    rma_line_id = fields.Many2one('rma.order.line', string='Original RMA Line')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    return_qty = fields.Float(string='Reported Return Qty', readonly=True)
    inspected_qty = fields.Float(string='Received & Inspected Qty', required=True, default=1.0)
    inspection_state = fields.Selection([
        ('passed', 'Quality Passed (Restock)'),
        ('repair', 'Needs Repair'),
        ('scrap', 'Scrapped / Defective'),
    ], string='Condition', default='passed', required=True)
    notes = fields.Char(string='Line Findings')
