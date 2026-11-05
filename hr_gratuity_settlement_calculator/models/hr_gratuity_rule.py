# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrGratuityRule(models.Model):
    _name = 'hr.gratuity.rule'
    _description = 'End of Service Gratuity Labor Law Rule'
    _order = 'name'

    name = fields.Char(string='Rule Name', required=True)
    code = fields.Char(string='Rule Code', required=True)
    active = fields.Boolean(default=True)
    country_id = fields.Many2one('res.country', string='Jurisdiction / Country')
    description = fields.Text(string='Labor Law Legal References & Scope')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )

    wage_type = fields.Selection([
        ('basic', 'Basic Salary Only'),
        ('gross', 'Gross Salary (Basic + Fixed Allowances)'),
    ], string='Calculation Wage Basis', default='basic', required=True)

    monthly_days_divisor = fields.Float(
        string='Monthly Daily Wage Divisor',
        default=30.0,
        required=True,
        help='Divisor used to calculate daily wage from monthly salary (usually 30.0 days).'
    )

    min_service_days = fields.Integer(
        string='Minimum Qualifying Service (Days)',
        default=365,
        required=True,
        help='Under UAE and KSA law, employees who serve less than 1 full year are not entitled to gratuity.'
    )

    # First Period Multiplier
    first_period_years = fields.Float(string='First Tier Threshold (Years)', default=5.0, required=True)
    first_period_days_per_year = fields.Float(
        string='First 5 Years Days/Year',
        default=21.0,
        required=True,
        help='UAE: 21 days basic salary per year. KSA: 15 days (half month) per year.'
    )

    # Subsequent Period Multiplier
    subsequent_days_per_year = fields.Float(
        string='Subsequent Years Days/Year',
        default=30.0,
        required=True,
        help='UAE: 30 days basic salary per year. KSA: 30 days (full month) per year.'
    )

    max_gratuity_years_cap = fields.Float(
        string='Maximum Cap (Years of Salary)',
        default=2.0,
        help='Maximum statutory gratuity cap. UAE sets maximum 2 years total basic salary (enter 2.0). 0 for no cap.'
    )

    # Resignation Rules
    resignation_rule_type = fields.Selection([
        ('equal', 'Equal to Termination (UAE Decree 33/2021: 100% Entitlement)'),
        ('ksa_tiered', 'Saudi Labor Law Article 85 (Tiered Resignation Reductions)'),
        ('custom', 'Custom Slotted Reductions'),
    ], string='Resignation Calculation Formula', default='equal', required=True)

    tier1_max_years = fields.Float(string='Tier 1 Service Limit (Years)', default=2.0)
    tier1_percentage = fields.Float(string='Tier 1 Entitlement (%)', default=0.0)

    tier2_max_years = fields.Float(string='Tier 2 Service Limit (Years)', default=5.0)
    tier2_percentage = fields.Float(string='Tier 2 Entitlement (%)', default=33.33)

    tier3_max_years = fields.Float(string='Tier 3 Service Limit (Years)', default=10.0)
    tier3_percentage = fields.Float(string='Tier 3 Entitlement (%)', default=66.67)

    tier4_percentage = fields.Float(string='Tier 4 Entitlement (> Tier 3) (%)', default=100.0)

    @api.constrains('first_period_years', 'monthly_days_divisor')
    def _check_parameters(self):
        for rec in self:
            if rec.monthly_days_divisor <= 0:
                raise ValidationError(_("Monthly days divisor must be strictly greater than 0."))
            if rec.first_period_years < 0:
                raise ValidationError(_("First period years cannot be negative."))
