# -*- coding: utf-8 -*-
from datetime import date
from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_overdue = fields.Boolean(
        string='Is Overdue',
        compute='_compute_overdue_metrics',
        search='_search_is_overdue',
        store=False
    )
    days_overdue = fields.Integer(
        string='Days Overdue',
        compute='_compute_overdue_metrics',
        search='_search_days_overdue',
        store=False
    )
    followup_level_id = fields.Many2one(
        'account.followup.level',
        string='Follow-up Level',
        compute='_compute_followup_level',
        store=False
    )

    @api.depends('invoice_date_due', 'state', 'payment_state', 'move_type')
    def _compute_overdue_metrics(self):
        today = fields.Date.context_today(self)
        for move in self:
            if (
                move.move_type == 'out_invoice'
                and move.state == 'posted'
                and move.payment_state in ('not_paid', 'partial')
                and move.invoice_date_due
                and move.invoice_date_due < today
            ):
                move.is_overdue = True
                move.days_overdue = (today - move.invoice_date_due).days
            else:
                move.is_overdue = False
                move.days_overdue = 0

    @api.depends('days_overdue', 'company_id')
    def _compute_followup_level(self):
        levels_by_company = {}
        for move in self:
            if not move.is_overdue:
                move.followup_level_id = False
                continue
            cid = move.company_id.id
            if cid not in levels_by_company:
                levels_by_company[cid] = self.env['account.followup.level'].search([
                    ('company_id', '=', cid),
                    ('active', '=', True)
                ], order='delay desc')
            
            matched = False
            for lvl in levels_by_company[cid]:
                if move.days_overdue >= lvl.delay:
                    move.followup_level_id = lvl
                    matched = True
                    break
            if not matched:
                move.followup_level_id = False

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<', today)
            ]
        return [
            '|', '|', '|',
            ('move_type', '!=', 'out_invoice'),
            ('state', '!=', 'posted'),
            ('payment_state', 'not in', ('not_paid', 'partial')),
            ('invoice_date_due', '>=', today)
        ]

    def _search_days_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        try:
            val_int = int(value)
        except (ValueError, TypeError):
            val_int = 0
        from datetime import timedelta
        target_date = today - timedelta(days=val_int)
        if operator in ('>', '>='):
            return [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '<=', target_date)
            ]
        elif operator in ('<', '<='):
            return [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
                ('invoice_date_due', '>=', target_date)
            ]
        return []
