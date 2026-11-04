# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class VendorScorecardPeriod(models.Model):
    _name = 'vendor.scorecard.period'
    _description = 'Vendor Scorecard Evaluation Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_to desc, id desc'

    name = fields.Char(string='Period / Campaign Title', required=True, tracking=True)
    date_from = fields.Date(string='Start Date', required=True, tracking=True)
    date_to = fields.Date(string='End Date', required=True, tracking=True)
    template_id = fields.Many2one(
        'vendor.scorecard.template',
        string='Scorecard Template',
        required=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('evaluated', 'Evaluated'),
        ('closed', 'Closed & Archived'),
    ], string='Status', default='draft', tracking=True)

    evaluation_ids = fields.One2many(
        'vendor.scorecard.evaluation',
        'period_id',
        string='Vendor Evaluations'
    )
    evaluation_count = fields.Integer(
        string='Total Evaluations',
        compute='_compute_evaluation_count'
    )
    grade_a_count = fields.Integer(string='Grade A Count', compute='_compute_grade_stats')
    grade_b_count = fields.Integer(string='Grade B Count', compute='_compute_grade_stats')
    grade_c_count = fields.Integer(string='Grade C Count', compute='_compute_grade_stats')
    grade_d_count = fields.Integer(string='Grade D Count', compute='_compute_grade_stats')

    @api.depends('evaluation_ids')
    def _compute_evaluation_count(self):
        for rec in self:
            rec.evaluation_count = len(rec.evaluation_ids)

    @api.depends('evaluation_ids.grade')
    def _compute_grade_stats(self):
        for rec in self:
            rec.grade_a_count = len(rec.evaluation_ids.filtered(lambda e: e.grade == 'grade_a'))
            rec.grade_b_count = len(rec.evaluation_ids.filtered(lambda e: e.grade == 'grade_b'))
            rec.grade_c_count = len(rec.evaluation_ids.filtered(lambda e: e.grade == 'grade_c'))
            rec.grade_d_count = len(rec.evaluation_ids.filtered(lambda e: e.grade == 'grade_d'))

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("Period Start Date cannot be later than End Date."))

    def action_start(self):
        for rec in self:
            rec.state = 'in_progress'

    def action_close(self):
        for rec in self:
            rec.evaluation_ids.action_publish()
            rec.state = 'closed'

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_generate_evaluations(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Please assign an Evaluation Template first."))

        # Find all vendors who have incoming pickings or POs in the period
        Picking = self.env['stock.picking']
        domain = [
            ('picking_type_id.code', '=', 'incoming'),
            ('date_done', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('date_done', '<=', fields.Datetime.to_datetime(self.date_to) + fields.Datetime.to_timedelta(days=1)),
            ('state', '=', 'done'),
            ('company_id', '=', self.company_id.id),
        ]
        pickings = Picking.search(domain)
        vendors = pickings.mapped('partner_id')

        # Also search purchase orders
        PO = self.env['purchase.order']
        po_domain = [
            ('date_approve', '>=', fields.Datetime.to_datetime(self.date_from)),
            ('date_approve', '<=', fields.Datetime.to_datetime(self.date_to) + fields.Datetime.to_timedelta(days=1)),
            ('state', 'in', ['purchase', 'done']),
            ('company_id', '=', self.company_id.id),
        ]
        orders = PO.search(po_domain)
        vendors |= orders.mapped('partner_id')

        if not vendors:
            raise UserError(_("No active vendors with completed receipts or confirmed purchase orders found in this period."))

        Evaluation = self.env['vendor.scorecard.evaluation']
        for vendor in vendors:
            evaluation = Evaluation.search([
                ('period_id', '=', self.id),
                ('partner_id', '=', vendor.id),
            ], limit=1)
            if not evaluation:
                evaluation = Evaluation.create({
                    'name': f"{self.name} - {vendor.display_name}",
                    'period_id': self.id,
                    'partner_id': vendor.id,
                    'template_id': self.template_id.id,
                    'company_id': self.company_id.id,
                })
            evaluation.action_compute_metrics()

        self.state = 'evaluated'
        return True

    def action_view_evaluations(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_vendor_scorecard_rating.action_vendor_scorecard_evaluation")
        action['domain'] = [('period_id', '=', self.id)]
        action['context'] = {'default_period_id': self.id}
        return action
