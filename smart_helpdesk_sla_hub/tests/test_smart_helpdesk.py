# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSmartHelpdeskSlaHub(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'name': 'Acme Industrial Support Client',
            'email': 'client@acme-support.example.com',
            'phone': '+1-555-0199',
        })
        cls.team = cls.env.ref('smart_helpdesk_sla_hub.helpdesk_team_customer_care')

    def test_01_ticket_creation_sla_and_resolution(self):
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Urgent Server Outage on Order S001',
            'partner_id': self.customer.id,
            'team_id': self.team.id,
            'priority': '3',
        })
        self.assertTrue(ticket.ticket_ref.startswith('TKT/'))
        self.assertEqual(ticket.partner_email, 'client@acme-support.example.com')
        self.assertTrue(ticket.sla_policy_id)
        self.assertEqual(ticket.sla_status, 'ongoing')

        # Start progress -> records first_response_date
        ticket.action_start_progress()
        self.assertTrue(ticket.first_response_date)
        self.assertTrue(ticket.stage_id.is_in_progress)

        # Resolve via wizard -> moves to Solved and achieves SLA
        wizard = self.env['helpdesk.ticket.resolve.wizard'].create({
            'ticket_id': ticket.id,
            'resolution_summary': 'Replaced faulty power supply module and verified uptime.',
            'customer_rating': '5',
        })
        wizard.action_confirm_resolve()
        self.assertTrue(ticket.is_close)
        self.assertEqual(ticket.sla_status, 'achieved')
        self.assertEqual(ticket.customer_rating, '5')

    def test_02_sla_breach_cron(self):
        ticket = self.env['helpdesk.ticket'].create({
            'name': 'Delayed Response Ticket',
            'partner_id': self.customer.id,
            'team_id': self.team.id,
            'priority': '2',
        })
        # Simulate past deadline
        ticket.sla_deadline = fields.Datetime.now() - timedelta(hours=2)
        self.env['helpdesk.ticket']._cron_check_sla_breaches()
        self.assertEqual(ticket.sla_status, 'failed')
