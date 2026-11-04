# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, tagged


@tagged('post_install', '-at_install')
class TestWhatsAppMessaging(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.customer = cls.env['res.partner'].create({
            'name': 'Global Trading Client Corp',
            'phone': '+1 (555) 345-6789',
            'email': 'client@globaltrading.com',
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Premium Enterprise Server Rack',
            'type': 'consu',
            'list_price': 2500.0,
        })
        cls.order = cls.env['sale.order'].create({
            'partner_id': cls.customer.id,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'name': cls.product.name,
                'product_uom_qty': 2.0,
                'price_unit': 2500.0,
            })],
        })
        cls.order.action_confirm()

    def test_01_template_rendering_and_placeholders(self):
        """Test placeholder substitution in whatsapp.template."""
        template = self.env['whatsapp.template'].create({
            'name': 'Test Quotation Template',
            'model_id': self.env['ir.model']._get_id('sale.order'),
            'header_text': 'Order Confirmation',
            'body': 'Dear ${partner_name}, your order ${document_number} of ${amount_total} is confirmed.',
            'footer_text': 'Thanks!',
        })

        rendered = template.render_template(self.order)
        self.assertIn('*Order Confirmation*', rendered)
        self.assertIn('Global Trading Client Corp', rendered)
        self.assertIn(self.order.name, rendered)
        self.assertIn(f"{self.order.amount_total:,.2f}", rendered)
        self.assertIn('_Thanks!_', rendered)

    def test_02_sale_order_whatsapp_dispatch(self):
        """Test launching wizard and dispatching WhatsApp message with audit log creation."""
        wizard = self.env['whatsapp.composer.wizard'].create({
            'partner_id': self.customer.id,
            'mobile_number': self.customer.phone,
            'message_body': 'Order %s is ready for delivery!' % self.order.name,
            'res_model': 'sale.order',
            'res_id': self.order.id,
            'record_ref': self.order.name,
        })

        action = wizard.action_send_whatsapp()
        self.assertEqual(action.get('type'), 'ir.actions.act_url')
        self.assertIn('15553456789', action.get('url'))
        self.assertIn('api.whatsapp.com', action.get('url'))

        # Verify audit log
        logs = self.env['whatsapp.message.log'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].mobile_number, '15553456789')
        self.assertEqual(logs[0].state, 'sent')
        self.assertEqual(self.order.whatsapp_log_count, 1)

    def test_03_phone_sanitization(self):
        """Test phone number cleaner removes spaces, plus signs, brackets, dashes."""
        wizard = self.env['whatsapp.composer.wizard'].new()
        clean = wizard._clean_phone_number('+44 (020) 7946-0912')
        self.assertEqual(clean, '4402079460912')

        clean2 = wizard._clean_phone_number('0091-98765-43210')
        self.assertEqual(clean2, '919876543210')
