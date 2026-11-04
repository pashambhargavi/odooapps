# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_scorecard_ids = fields.One2many(
        'vendor.scorecard.evaluation',
        'partner_id',
        string='Scorecard History'
    )
    latest_scorecard_id = fields.Many2one(
        'vendor.scorecard.evaluation',
        string='Latest Evaluation Scorecard',
        readonly=True,
        tracking=True
    )
    supplier_grade = fields.Selection([
        ('grade_a', 'Grade A - Preferred Partner'),
        ('grade_b', 'Grade B - Approved Supplier'),
        ('grade_c', 'Grade C - Conditional / Warning'),
        ('grade_d', 'Grade D - Blacklisted / Restricted'),
    ], string='Vendor Quality Grade', readonly=True, tracking=True)

    supplier_score = fields.Float(
        string='Current Score (%)',
        readonly=True,
        tracking=True
    )
    supplier_evaluation_count = fields.Integer(
        string='Evaluation Count',
        compute='_compute_supplier_evaluation_count'
    )

    @api.depends('vendor_scorecard_ids')
    def _compute_supplier_evaluation_count(self):
        for rec in self:
            rec.supplier_evaluation_count = len(rec.vendor_scorecard_ids)

    def action_view_vendor_scorecards(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_vendor_scorecard_rating.action_vendor_scorecard_evaluation")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {'default_partner_id': self.id}
        return action
