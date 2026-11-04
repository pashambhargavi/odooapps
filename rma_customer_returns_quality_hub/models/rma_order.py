# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class RmaOrder(models.Model):
    _name = 'rma.order'
    _description = 'Return Merchandise Authorization (RMA)'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _check_company_auto = True

    name = fields.Char(
        string='RMA Number', required=True, copy=False, readonly=True,
        index='trigram', default=lambda self: _('New')
    )
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True,
        check_company=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        related='company_id.currency_id', string='Currency', readonly=True
    )
    user_id = fields.Many2one(
        'res.users', string='Responsible Agent', default=lambda self: self.env.user,
        tracking=True
    )
    date_rma = fields.Datetime(
        string='RMA Date', default=fields.Datetime.now, required=True, tracking=True
    )
    sale_id = fields.Many2one(
        'sale.order', string='Sales Order Reference', tracking=True,
        check_company=True
    )
    picking_id = fields.Many2one(
        'stock.picking', string='Source Delivery Order', tracking=True,
        check_company=True
    )
    invoice_id = fields.Many2one(
        'account.move', string='Source Invoice Reference', tracking=True,
        domain="[('move_type', '=', 'out_invoice')]", check_company=True
    )
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Receiving Warehouse', required=True,
        default=lambda self: self._default_warehouse_id(), check_company=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved (Waiting Receipt)'),
        ('received', 'Goods Received'),
        ('inspected', 'Inspected'),
        ('resolved', 'Resolved / Closed'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, copy=False, tracking=True)

    resolution_type = fields.Selection([
        ('refund', 'Credit Note / Refund'),
        ('replacement', 'Free Replacement Delivery'),
        ('repair', 'Internal Repair'),
        ('scrap', 'Scrap Without Refund'),
    ], string='Resolution Type', default='refund', tracking=True)

    line_ids = fields.One2many(
        'rma.order.line', 'rma_id', string='RMA Lines', copy=True
    )
    total_returned_qty = fields.Float(
        string='Total Return Units', compute='_compute_totals', store=True
    )
    total_refund_amount = fields.Monetary(
        string='Total Estimated Refund', compute='_compute_totals', store=True
    )

    return_picking_id = fields.Many2one(
        'stock.picking', string='Return Receipt Operation', readonly=True, copy=False
    )
    replacement_picking_id = fields.Many2one(
        'stock.picking', string='Replacement Delivery Operation', readonly=True, copy=False
    )
    credit_note_id = fields.Many2one(
        'account.move', string='Customer Credit Note', readonly=True, copy=False
    )

    return_picking_count = fields.Integer(compute='_compute_counts')
    replacement_picking_count = fields.Integer(compute='_compute_counts')
    credit_note_count = fields.Integer(compute='_compute_counts')

    note = fields.Html(string='Customer & Operational Notes')
    rejection_reason = fields.Text(string='Rejection Explanation', copy=False)

    @api.model
    def _default_warehouse_id(self):
        return self.env['stock.warehouse'].search([
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    @api.depends('line_ids.return_qty', 'line_ids.refund_subtotal')
    def _compute_totals(self):
        for rma in self:
            rma.total_returned_qty = sum(rma.line_ids.mapped('return_qty'))
            rma.total_refund_amount = sum(rma.line_ids.mapped('refund_subtotal'))

    def _compute_counts(self):
        for rma in self:
            rma.return_picking_count = 1 if rma.return_picking_id else 0
            rma.replacement_picking_count = 1 if rma.replacement_picking_id else 0
            rma.credit_note_count = 1 if rma.credit_note_id else 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('rma.order.seq') or _('New')
        return super().create(vals_list)

    def action_approve(self):
        for rma in self:
            if not rma.line_ids:
                raise UserError(_('Cannot approve an RMA ticket without any product lines.'))
            rma.state = 'approved'
            rma.message_post(body=_('RMA Request approved. Customer Return Slip can now be issued.'))

    def action_receive_goods(self):
        """Creates reverse stock picking (incoming return to warehouse)."""
        self.ensure_one()
        if not self.warehouse_id:
            raise UserError(_('Please configure a Receiving Warehouse on this RMA.'))

        picking_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', self.warehouse_id.id),
            ('code', '=', 'incoming'),
        ], limit=1)
        if not picking_type:
            raise UserError(_('No incoming picking type found for warehouse %s.') % self.warehouse_id.name)

        customer_loc = self.partner_id.property_stock_customer or self.env.ref('stock.stock_location_customers')
        dest_loc = self.warehouse_id.lot_stock_id

        moves = []
        for line in self.line_ids.filtered(lambda l: l.return_qty > 0):
            moves.append((0, 0, {
                'description_picking': _('RMA Return: %s') % line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.return_qty,
                'product_uom': line.product_uom_id.id or line.product_id.uom_id.id,
                'location_id': customer_loc.id,
                'location_dest_id': dest_loc.id,
                'company_id': self.company_id.id,
            }))

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': customer_loc.id,
            'location_dest_id': dest_loc.id,
            'move_ids': moves,
            'company_id': self.company_id.id,
            'rma_id': self.id,
        })
        self.return_picking_id = picking.id
        self.state = 'received'
        self.message_post(body=_('Return Receipt operation %s created.') % picking.name)
        return self.action_view_return_picking()

    def action_open_inspection_wizard(self):
        self.ensure_one()
        return {
            'name': _('RMA Quality Inspection Workbench'),
            'type': 'ir.actions.act_window',
            'res_model': 'rma.inspection.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_rma_id': self.id},
        }

    def action_create_credit_note(self):
        """Creates customer refund credit note in Invoicing."""
        self.ensure_one()
        if self.credit_note_id:
            return self.action_view_credit_note()

        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            raise UserError(_('No Sales Journal configured for company %s.') % self.company_id.name)

        invoice_lines = []
        for line in self.line_ids.filtered(lambda l: l.return_qty > 0 and l.refund_subtotal > 0):
            invoice_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': line.return_qty,
                'price_unit': line.unit_price,
                'name': _('RMA Return: %s (%s)') % (line.product_id.display_name, self.name),
            }))

        credit_note = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_id.id,
            'journal_id': journal.id,
            'currency_id': self.currency_id.id,
            'invoice_date': fields.Date.context_today(self),
            'ref': _('RMA: %s') % self.name,
            'invoice_line_ids': invoice_lines,
            'company_id': self.company_id.id,
            'rma_id': self.id,
        })
        self.credit_note_id = credit_note.id
        self.message_post(body=_('Customer Refund Credit Note %s created.') % credit_note.name)
        return self.action_view_credit_note()

    def action_create_replacement_delivery(self):
        """Creates free replacement dispatch order."""
        self.ensure_one()
        if self.replacement_picking_id:
            return self.action_view_replacement_picking()

        picking_type = self.warehouse_id.out_type_id
        if not picking_type:
            raise UserError(_('No delivery picking type found for warehouse %s.') % self.warehouse_id.name)

        src_loc = self.warehouse_id.lot_stock_id
        customer_loc = self.partner_id.property_stock_customer or self.env.ref('stock.stock_location_customers')

        moves = []
        for line in self.line_ids.filtered(lambda l: l.return_qty > 0):
            moves.append((0, 0, {
                'description_picking': _('RMA Replacement: %s') % line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.return_qty,
                'product_uom': line.product_uom_id.id or line.product_id.uom_id.id,
                'location_id': src_loc.id,
                'location_dest_id': customer_loc.id,
                'company_id': self.company_id.id,
            }))

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': _('Replacement for %s') % self.name,
            'location_id': src_loc.id,
            'location_dest_id': customer_loc.id,
            'move_ids': moves,
            'company_id': self.company_id.id,
            'rma_id': self.id,
        })
        self.replacement_picking_id = picking.id
        self.message_post(body=_('Replacement Delivery %s created.') % picking.name)
        return self.action_view_replacement_picking()

    def action_resolve(self):
        for rma in self:
            rma.state = 'resolved'
            rma.message_post(body=_('RMA order marked as resolved and closed.'))

    def action_reject(self):
        for rma in self:
            rma.state = 'rejected'
            rma.message_post(body=_('RMA order has been rejected.'))

    def action_set_to_draft(self):
        for rma in self:
            if rma.return_picking_id and rma.return_picking_id.state == 'done':
                raise UserError(_('Cannot reset to draft: return receipt has already been processed.'))
            rma.state = 'draft'

    def action_view_return_picking(self):
        self.ensure_one()
        return {
            'name': _('Return Receipt Operation'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.return_picking_id.id,
        }

    def action_view_replacement_picking(self):
        self.ensure_one()
        return {
            'name': _('Replacement Delivery Operation'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.replacement_picking_id.id,
        }

    def action_view_credit_note(self):
        self.ensure_one()
        return {
            'name': _('Customer Refund Credit Note'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.credit_note_id.id,
        }
