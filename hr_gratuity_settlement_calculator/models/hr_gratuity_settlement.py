# -*- coding: utf-8 -*-
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HrGratuitySettlement(models.Model):
    _name = 'hr.gratuity.settlement'
    _description = 'End of Service Gratuity & Final Settlement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'leaving_date desc, id desc'

    name = fields.Char(
        string='Settlement Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        tracking=True
    )
    department_id = fields.Many2one(
        'hr.department',
        related='employee_id.department_id',
        string='Department',
        readonly=True
    )
    job_id = fields.Many2one(
        'hr.job',
        related='employee_id.job_id',
        string='Job Position',
        readonly=True
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )

    joining_date = fields.Date(
        string='Date of Joining',
        required=True,
        tracking=True
    )
    leaving_date = fields.Date(
        string='Last Working Day',
        default=fields.Date.context_today,
        required=True,
        tracking=True
    )
    departure_reason = fields.Selection([
        ('termination', 'Employer Termination (Non-Renewal / Redundancy)'),
        ('resignation', 'Employee Resignation'),
        ('contract_expiry', 'Fixed-Term Contract Expiration'),
        ('mutual', 'Mutual Separation Agreement'),
        ('retirement', 'Retirement / Medical Disability'),
    ], string='Separation Reason', default='resignation', required=True, tracking=True)

    gratuity_rule_id = fields.Many2one(
        'hr.gratuity.rule',
        string='Labor Law Gratuity Rule',
        required=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft Work-in-Progress'),
        ('calculated', 'Gratuity Calculated'),
        ('cleared', 'Department Clearance Completed'),
        ('approved', 'Management Approved'),
        ('posted', 'Accounting Posted'),
        ('paid', 'Paid & Closed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    # Service Metrics
    total_days_worked = fields.Integer(string='Total Calendar Days Worked', compute='_compute_service_duration', store=True)
    service_years = fields.Float(string='Exact Service (Years)', compute='_compute_service_duration', store=True)
    service_display = fields.Char(string='Tenure Breakdown', compute='_compute_service_duration', store=True)

    # Salary Basis
    basic_salary = fields.Monetary(string='Monthly Basic Salary', currency_field='currency_id', required=True, tracking=True)
    allowances_amount = fields.Monetary(string='Fixed Monthly Allowances', currency_field='currency_id', default=0.0)
    gross_salary = fields.Monetary(string='Gross Monthly Package', currency_field='currency_id', compute='_compute_wages', store=True)
    calculation_wage = fields.Monetary(string='Statutory Calculation Wage', currency_field='currency_id', compute='_compute_wages', store=True)
    daily_wage = fields.Monetary(string='Calculated Daily Wage', currency_field='currency_id', compute='_compute_wages', store=True)

    # Entitlements
    gratuity_amount = fields.Monetary(string='End of Service Gratuity', currency_field='currency_id', compute='_compute_gratuity', store=True, tracking=True)
    unused_leave_days = fields.Float(string='Unused Annual Leave (Days)', default=0.0)
    leave_salary_encashment = fields.Monetary(string='Leave Salary Encashment', currency_field='currency_id', compute='_compute_leave_encashment', store=True)
    pending_salary_days = fields.Float(string='Unpaid Days in Final Month', default=0.0)
    pending_salary_amount = fields.Monetary(string='Unpaid Final Salary', currency_field='currency_id', compute='_compute_pending_salary', store=True)
    air_ticket_amount = fields.Monetary(string='Repatriation Airfare Allowance', currency_field='currency_id', default=0.0)

    notice_pay_type = fields.Selection([
        ('none', 'No Notice Period Adjustment'),
        ('payable', 'Payable to Employee (In-Lieu of Notice)'),
        ('deducted', 'Deducted from Employee (Short Notice Penalty)'),
    ], string='Notice Period Settlement', default='none')
    notice_pay_amount = fields.Monetary(string='Notice Pay Amount', currency_field='currency_id', default=0.0)
    other_allowances = fields.Monetary(string='Other Discretionary Allowances', currency_field='currency_id', default=0.0)
    total_entitlements = fields.Monetary(string='Gross Entitlements', currency_field='currency_id', compute='_compute_totals', store=True)

    # Deductions
    loan_deduction = fields.Monetary(string='Outstanding Loan / Advance', currency_field='currency_id', default=0.0)
    asset_damage_deduction = fields.Monetary(string='Asset Loss / Property Damage', currency_field='currency_id', default=0.0)
    other_deductions = fields.Monetary(string='Other Deductions', currency_field='currency_id', default=0.0)
    total_deductions = fields.Monetary(string='Total Deductions', currency_field='currency_id', compute='_compute_totals', store=True)

    # Net Settlement
    net_payable = fields.Monetary(string='Net End-of-Service Payable', currency_field='currency_id', compute='_compute_totals', store=True, tracking=True)

    # Clearance Checklist
    clearance_it = fields.Boolean(string='IT Asset Clearance (Laptop, Access & Email)')
    clearance_it_user_id = fields.Many2one('res.users', string='IT Officer Sign-off')
    clearance_finance = fields.Boolean(string='Finance Clearance (Loans, Credit Cards, Petty Cash)')
    clearance_finance_user_id = fields.Many2one('res.users', string='Finance Officer Sign-off')
    clearance_admin = fields.Boolean(string='Admin Clearance (Access Badge, Office Keys, Vehicle)')
    clearance_admin_user_id = fields.Many2one('res.users', string='Admin Officer Sign-off')
    clearance_hr = fields.Boolean(string='HR Clearance (Visa Cancellation & Medical Insurance)')
    clearance_hr_user_id = fields.Many2one('res.users', string='HR Officer Sign-off')
    all_cleared = fields.Boolean(string='All Departments Cleared', compute='_compute_clearance_status', store=True)

    # Accounting Integration
    journal_id = fields.Many2one('account.journal', string='Settlement Journal', domain="[('type', 'in', ['general', 'purchase'])]")
    account_expense_id = fields.Many2one('account.account', string='Gratuity Expense Account')
    account_liability_id = fields.Many2one('account.account', string='Gratuity Liability / Payable Account')
    move_id = fields.Many2one('account.move', string='Generated Accounting Entry', readonly=True, copy=False)

    notes = fields.Text(string='Settlement Assessment & Legal Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq = self.env['ir.sequence'].next_by_code('hr.gratuity.settlement') or _('New')
                vals['name'] = seq
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id:
            # Set default joining date
            self.joining_date = getattr(self.employee_id, 'first_contract_date', False) or getattr(self.employee_id, 'create_date', fields.Date.today())
            # Find default gratuity rule
            rule = self.env['hr.gratuity.rule'].search([('company_id', '=', self.company_id.id)], limit=1)
            if rule:
                self.gratuity_rule_id = rule.id

    @api.depends('joining_date', 'leaving_date')
    def _compute_service_duration(self):
        for rec in self:
            if rec.joining_date and rec.leaving_date and rec.leaving_date >= rec.joining_date:
                delta = rec.leaving_date - rec.joining_date
                rec.total_days_worked = delta.days + 1
                rec.service_years = round(rec.total_days_worked / 365.25, 4)

                rd = relativedelta(rec.leaving_date, rec.joining_date)
                rec.service_display = f"{rd.years} Years, {rd.months} Months, {rd.days} Days"
            else:
                rec.total_days_worked = 0
                rec.service_years = 0.0
                rec.service_display = "0 Days"

    @api.depends('basic_salary', 'allowances_amount', 'gratuity_rule_id')
    def _compute_wages(self):
        for rec in self:
            rec.gross_salary = rec.basic_salary + rec.allowances_amount
            divisor = rec.gratuity_rule_id.monthly_days_divisor if rec.gratuity_rule_id else 30.0
            if divisor <= 0:
                divisor = 30.0

            if rec.gratuity_rule_id and rec.gratuity_rule_id.wage_type == 'gross':
                rec.calculation_wage = rec.gross_salary
            else:
                rec.calculation_wage = rec.basic_salary

            rec.daily_wage = round(rec.calculation_wage / divisor, 2)

    @api.depends('unused_leave_days', 'daily_wage')
    def _compute_leave_encashment(self):
        for rec in self:
            rec.leave_salary_encashment = round(rec.unused_leave_days * rec.daily_wage, 2)

    @api.depends('pending_salary_days', 'daily_wage')
    def _compute_pending_salary(self):
        for rec in self:
            rec.pending_salary_amount = round(rec.pending_salary_days * rec.daily_wage, 2)

    @api.depends('service_years', 'total_days_worked', 'daily_wage', 'departure_reason', 'gratuity_rule_id', 'calculation_wage')
    def _compute_gratuity(self):
        for rec in self:
            rule = rec.gratuity_rule_id
            if not rule or rec.total_days_worked < rule.min_service_days:
                rec.gratuity_amount = 0.0
                continue

            years = rec.service_years
            daily = rec.daily_wage
            gratuity = 0.0

            # 1. Base Gratuity Formula
            if years <= rule.first_period_years:
                gratuity = years * rule.first_period_days_per_year * daily
            else:
                first_tier = rule.first_period_years * rule.first_period_days_per_year * daily
                subsequent_years = years - rule.first_period_years
                subsequent_tier = subsequent_years * rule.subsequent_days_per_year * daily
                gratuity = first_tier + subsequent_tier

            # 2. Resignation Reductions
            if rec.departure_reason == 'resignation':
                if rule.resignation_rule_type == 'ksa_tiered':
                    if years < rule.tier1_max_years:
                        gratuity = gratuity * (rule.tier1_percentage / 100.0)
                    elif years < rule.tier2_max_years:
                        gratuity = gratuity * (rule.tier2_percentage / 100.0)
                    elif years < rule.tier3_max_years:
                        gratuity = gratuity * (rule.tier3_percentage / 100.0)
                    else:
                        gratuity = gratuity * (rule.tier4_percentage / 100.0)
                elif rule.resignation_rule_type == 'custom':
                    gratuity = gratuity * (rule.tier2_percentage / 100.0)
                # equal: 100% full entitlement under UAE Decree 33

            # 3. Maximum Statutory Cap (e.g. 2 years' salary)
            if rule.max_gratuity_years_cap > 0:
                max_cap = rule.max_gratuity_years_cap * 12.0 * rec.calculation_wage
                gratuity = min(gratuity, max_cap)

            rec.gratuity_amount = round(gratuity, 2)

    @api.depends(
        'gratuity_amount', 'leave_salary_encashment', 'pending_salary_amount',
        'air_ticket_amount', 'notice_pay_type', 'notice_pay_amount', 'other_allowances',
        'loan_deduction', 'asset_damage_deduction', 'other_deductions'
    )
    def _compute_totals(self):
        for rec in self:
            # Entitlements
            entitlements = rec.gratuity_amount + rec.leave_salary_encashment + rec.pending_salary_amount + rec.air_ticket_amount + rec.other_allowances
            if rec.notice_pay_type == 'payable':
                entitlements += rec.notice_pay_amount

            # Deductions
            deductions = rec.loan_deduction + rec.asset_damage_deduction + rec.other_deductions
            if rec.notice_pay_type == 'deducted':
                deductions += rec.notice_pay_amount

            rec.total_entitlements = round(entitlements, 2)
            rec.total_deductions = round(deductions, 2)
            rec.net_payable = round(entitlements - deductions, 2)

    @api.depends('clearance_it', 'clearance_finance', 'clearance_admin', 'clearance_hr')
    def _compute_clearance_status(self):
        for rec in self:
            rec.all_cleared = (rec.clearance_it and rec.clearance_finance and rec.clearance_admin and rec.clearance_hr)

    def action_calculate_gratuity(self):
        for rec in self:
            rec._compute_service_duration()
            rec._compute_wages()
            rec._compute_leave_encashment()
            rec._compute_pending_salary()
            rec._compute_gratuity()
            rec._compute_totals()
            rec.state = 'calculated'

    def action_sign_clearance(self):
        for rec in self:
            if not rec.all_cleared:
                raise UserError(_("Please ensure all 4 department clearance checkboxes (IT, Finance, Admin, HR) are verified and signed."))
            rec.state = 'cleared'

    def action_approve(self):
        for rec in self:
            if rec.state not in ['calculated', 'cleared']:
                raise UserError(_("Settlement must be calculated and department-cleared before approval."))
            rec.state = 'approved'

    def action_post_accounting_entry(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError(_("Settlement must be approved before generating general ledger entries."))
            if rec.move_id:
                raise UserError(_("An accounting entry has already been posted for this settlement."))

            if not rec.journal_id or not rec.account_expense_id or not rec.account_liability_id:
                raise UserError(_("Please configure the Settlement Journal, Expense Account, and Liability Account."))

            # Debit Gratuity Expense, Credit Employee Payable Liability
            move_vals = {
                'journal_id': rec.journal_id.id,
                'date': rec.leaving_date,
                'ref': f"End of Service Settlement: {rec.name} ({rec.employee_id.name})",
                'line_ids': [
                    (0, 0, {
                        'name': f"EOS Gratuity Expense - {rec.employee_id.name}",
                        'account_id': rec.account_expense_id.id,
                        'debit': rec.net_payable,
                        'credit': 0.0,
                    }),
                    (0, 0, {
                        'name': f"EOS Accrued Liability - {rec.employee_id.name}",
                        'account_id': rec.account_liability_id.id,
                        'debit': 0.0,
                        'credit': rec.net_payable,
                    }),
                ]
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            rec.move_id = move.id
            rec.state = 'posted'

    def action_mark_paid(self):
        for rec in self:
            rec.state = 'paid'

    def action_reset_draft(self):
        for rec in self:
            if rec.move_id and rec.move_id.state != 'draft':
                raise UserError(_("Cannot reset to draft while a posted accounting entry exists. Please reverse or cancel the journal entry first."))
            rec.state = 'draft'

    def action_print_settlement_report(self):
        self.ensure_one()
        return self.env.ref('hr_gratuity_settlement_calculator.action_report_hr_gratuity_settlement').report_action(self)
