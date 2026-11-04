# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    supplier_grade = fields.Selection(
        related='partner_id.supplier_grade',
        string='Supplier Grade',
        readonly=True
    )
    supplier_score = fields.Float(
        related='partner_id.supplier_score',
        string='Supplier Score (%)',
        readonly=True
    )
    supplier_grade_warning = fields.Char(
        string='Supplier Evaluation Alert',
        compute='_compute_supplier_grade_warning'
    )

    @api.depends('partner_id', 'partner_id.supplier_grade', 'partner_id.supplier_score')
    def _compute_supplier_grade_warning(self):
        for order in self:
            grade = order.partner_id.supplier_grade
            score = order.partner_id.supplier_score
            if grade == 'grade_d':
                order.supplier_grade_warning = _(
                    "RESTRICTED SUPPLIER ALERT: %(name)s holds Grade D (Score: %(score).1f%%). Procurement Manager approval is required.",
                    name=order.partner_id.name,
                    score=score
                )
            elif grade == 'grade_c':
                order.supplier_grade_warning = _(
                    "CONDITIONAL SUPPLIER: %(name)s holds Grade C (Score: %(score).1f%%). Please verify delivery lead times and packaging.",
                    name=order.partner_id.name,
                    score=score
                )
            else:
                order.supplier_grade_warning = False

    def button_confirm(self):
        for order in self:
            if order.partner_id.supplier_grade == 'grade_d':
                # Check if current user is Scorecard / Purchase Manager
                is_manager = self.env.user.has_group('purchase_vendor_scorecard_rating.group_scorecard_manager')
                if not is_manager:
                    raise UserError(_(
                        "Cannot confirm Purchase Order for '%(name)s'. The supplier is currently Grade D (Restricted/Blacklisted). Only a Procurement Manager or Comptroller can release this order.",
                        name=order.partner_id.name
                    ))
        return super().button_confirm()
