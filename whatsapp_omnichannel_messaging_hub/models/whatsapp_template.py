# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class WhatsAppTemplate(models.Model):
    _name = 'whatsapp.template'
    _description = 'WhatsApp Message Template'
    _order = 'sequence, name'

    name = fields.Char(string='Template Title', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)
    model_id = fields.Many2one(
        'ir.model', string='Applies To Model', required=True, ondelete='cascade',
        help='Target business model (e.g. Sales Order, Invoice, Delivery Slip, Contact).',
    )
    model = fields.Char(string='Model Technical Name', related='model_id.model', readonly=True, store=True)
    body = fields.Text(
        string='Message Template Body', required=True,
        help='Message text. Use placeholders like ${partner_name}, ${amount_total}, ${name}, ${company_name}.'
    )
    header_text = fields.Char(string='Header Text (Optional)', help='Greeting or bold announcement.')
    footer_text = fields.Char(string='Footer Text (Optional)', help='Closing signature or disclaimer.')
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company,
    )

    def render_template(self, record):
        """Replaces placeholders in the body with actual field values from the record."""
        self.ensure_one()
        rendered = self.body or ""

        # Map common standard placeholders
        partner = getattr(record, 'partner_id', False) or (record if record._name == 'res.partner' else False)
        company = getattr(record, 'company_id', False) or self.env.company
        user = getattr(record, 'user_id', False) or getattr(record, 'invoice_user_id', False) or self.env.user

        doc_name = getattr(record, 'name', '')
        partner_name = partner.name if partner else ''
        company_name = company.name if company else ''
        user_name = user.name if user else ''
        
        amount_total = ""
        currency_symbol = ""
        if hasattr(record, 'amount_total'):
            currency = getattr(record, 'currency_id', False) or company.currency_id
            currency_symbol = currency.symbol or currency.name or ""
            amount_total = f"{currency_symbol} {record.amount_total:,.2f}"

        due_date = ""
        if hasattr(record, 'invoice_date_due') and record.invoice_date_due:
            due_date = str(record.invoice_date_due)
        elif hasattr(record, 'date_order') and record.date_order:
            due_date = str(record.date_order.date()) if hasattr(record.date_order, 'date') else str(record.date_order)

        tracking_ref = getattr(record, 'carrier_tracking_ref', '') or getattr(record, 'origin', '')

        # Standard dictionary replacement
        placeholders = {
            '${partner_name}': partner_name,
            '${name}': doc_name,
            '${document_number}': doc_name,
            '${amount_total}': amount_total,
            '${due_date}': due_date,
            '${company_name}': company_name,
            '${user_name}': user_name,
            '${tracking_number}': tracking_ref,
        }
        for k, v in placeholders.items():
            rendered = rendered.replace(k, str(v))

        # Dynamic field regex replacement for any other ${field_name}
        def repl(match):
            fname = match.group(1)
            val = getattr(record, fname, '')
            if hasattr(val, 'name'):
                return str(val.name)
            return str(val) if val is not False and val is not None else ''

        rendered = re.sub(r'\$\{([a-zA-Z0-9_]+)\}', repl, rendered)

        # Assemble full message with optional header/footer
        full_msg = []
        if self.header_text:
            full_msg.append(f"*{self.header_text}*")
        full_msg.append(rendered)
        if self.footer_text:
            full_msg.append(f"_{self.footer_text}_")

        return "\n\n".join(full_msg)
