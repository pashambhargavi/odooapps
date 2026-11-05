# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class QmsNcr(models.Model):
    _name = 'qms.ncr'
    _description = 'Quality Non-Conformance Report (NCR)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='NCR Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    title = fields.Char(
        string='Non-Conformance Title',
        required=True,
        tracking=True
    )
    source_type = fields.Selection([
        ('internal', 'Internal Production / Warehouse'),
        ('supplier', 'Supplier Defect (Incoming Receipt)'),
        ('customer', 'Customer Complaint / Return'),
        ('audit', 'Audit Finding (Internal / ISO)'),
    ], string='Source Type', default='internal', required=True, tracking=True)

    partner_id = fields.Many2one('res.partner', string='Customer / Vendor', tracking=True)
    product_id = fields.Many2one('product.product', string='Defective Product', tracking=True)
    lot_id = fields.Many2one('stock.lot', string='Lot / Serial Number', domain="[('product_id', '=', product_id)]")
    qty_affected = fields.Float(string='Quantity Affected', default=1.0, tracking=True)
    qty_rejected = fields.Float(string='Quantity Quarantined / Rejected', default=1.0, tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True)

    severity = fields.Selection([
        ('minor', 'Minor (Negligible Quality Impact)'),
        ('major', 'Major (Form/Fit/Function Compromised)'),
        ('critical', 'Critical (Safety, Regulatory or Total Failure)'),
    ], string='Severity Level', default='minor', required=True, tracking=True)

    detection_stage = fields.Selection([
        ('incoming', 'Incoming Inspection / Receiving'),
        ('in_process', 'In-Process Manufacturing'),
        ('final_qa', 'Final Inspection & Packaging'),
        ('customer_site', 'Customer Field Failure / In-Use'),
    ], string='Detection Stage', default='in_process', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('under_review', 'Under QA Review'),
        ('quarantined', 'Quarantined & Contained'),
        ('capa_required', 'CAPA In Progress'),
        ('closed', 'Closed & Resolved'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    description = fields.Text(string='Defect Description & Findings', required=True)
    containment_action = fields.Text(string='Immediate Containment Action', tracking=True)
    disposition = fields.Selection([
        ('pending', 'Pending Evaluation'),
        ('scrap', 'Scrap / Dispose'),
        ('rework', 'Rework / Recondition'),
        ('return_vendor', 'Return to Vendor (RTV)'),
        ('concession', 'Use As-Is (Deviation / Concession)'),
    ], string='Material Disposition', default='pending', tracking=True)

    quarantine_location_id = fields.Many2one(
        'stock.location',
        string='Quarantine Stock Location',
        domain="[('usage', '=', 'internal')]"
    )
    stock_picking_id = fields.Many2one('stock.picking', string='Related Inventory Transfer')
    purchase_order_id = fields.Many2one('purchase.order', string='Related Purchase Order')
    sale_order_id = fields.Many2one('sale.order', string='Related Sales Order')

    user_id = fields.Many2one('res.users', string='Reported By', default=lambda self: self.env.user, tracking=True)
    qa_manager_id = fields.Many2one('res.users', string='Quality Lead / Manager', tracking=True)
    close_date = fields.Date(string='Closure Date', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    capa_ids = fields.One2many('qms.capa', 'ncr_id', string='Corrective & Preventive Actions (CAPA)')
    capa_count = fields.Integer(string='CAPA Count', compute='_compute_capa_count')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qms.ncr') or _('New')
        return super().create(vals_list)

    @api.depends('capa_ids')
    def _compute_capa_count(self):
        for record in self:
            record.capa_count = len(record.capa_ids)

    def action_submit(self):
        for record in self:
            record.write({'state': 'under_review'})

    def action_quarantine(self):
        for record in self:
            if not record.containment_action:
                raise UserError(_("Please define the Immediate Containment Action before placing defective items into Quarantine."))
            record.write({'state': 'quarantined'})

    def action_create_capa(self):
        self.ensure_one()
        capa = self.env['qms.capa'].create({
            'title': _("CAPA for %s: %s") % (self.name, self.title),
            'ncr_id': self.id,
            'source': 'ncr',
            'product_id': self.product_id.id,
            'partner_id': self.partner_id.id,
            'problem_statement': self.description,
            'containment_actions': self.containment_action or _("Immediate containment executed under NCR %s") % self.name,
            'assigned_to_id': self.qa_manager_id.id or self.env.user.id,
            'company_id': self.company_id.id,
        })
        self.write({'state': 'capa_required'})
        return {
            'name': _('Corrective Action (CAPA)'),
            'type': 'ir.actions.act_window',
            'res_model': 'qms.capa',
            'view_mode': 'form',
            'res_id': capa.id,
            'target': 'current',
        }

    def action_view_capa(self):
        self.ensure_one()
        action = self.env.ref('iso_quality_management_qms.action_qms_capa').read()[0]
        action['domain'] = [('ncr_id', '=', self.id)]
        action['context'] = {'default_ncr_id': self.id}
        return action

    def action_close(self):
        for record in self:
            if record.disposition == 'pending':
                raise UserError(_("Please assign a Material Disposition (e.g., Scrap, Rework, Return) before closing this Non-Conformance."))
            record.write({
                'state': 'closed',
                'close_date': fields.Date.today(),
            })

    def action_cancel(self):
        for record in self:
            record.write({'state': 'cancelled'})
