# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AssetAuditSession(models.Model):
    _name = 'asset.audit.session'
    _description = 'Physical Asset Barcode Audit Session'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Audit Reference', readonly=True, copy=False, default=lambda self: _('New'))
    audit_date = fields.Date(string='Audit Date', default=fields.Date.today, required=True, tracking=True)
    auditor_id = fields.Many2one('res.users', string='Lead Auditor', default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)

    target_location = fields.Char(string='Audit Facility / Location', default='All Locations',
                                  help='E.g. "HQ Building / Floor 1", "Warehouse Bay B", or "All Locations"')
    category_id = fields.Many2one('account.asset.pro.category', string='Filter by Category',
                                  help='Limit audit to specific asset category, or leave blank to scan all assets.')

    barcode_scan_input = fields.Char(string='Live Barcode / QR Scanner Input',
                                     help='Scan physical barcode or QR label using laser scanner or mobile camera.')

    state = fields.Selection([
        ('draft', 'Draft Scheduled'),
        ('in_progress', 'Audit In Progress'),
        ('done', 'Completed & Reconciled'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('asset.audit.session.line', 'session_id', string='Audit Lines')

    total_expected = fields.Integer(string='Expected Assets', compute='_compute_audit_metrics', store=True)
    total_verified = fields.Integer(string='Verified Present', compute='_compute_audit_metrics', store=True)
    total_missing = fields.Integer(string='Missing / Unaccounted', compute='_compute_audit_metrics', store=True)
    total_discrepant = fields.Integer(string='Discrepant / Wrong Location', compute='_compute_audit_metrics', store=True)

    @api.depends('line_ids.status')
    def _compute_audit_metrics(self):
        for session in self:
            session.total_expected = len(session.line_ids)
            session.total_verified = len(session.line_ids.filtered(lambda l: l.status == 'verified'))
            session.total_missing = len(session.line_ids.filtered(lambda l: l.status in ('pending', 'missing')))
            session.total_discrepant = len(session.line_ids.filtered(lambda l: l.status in ('wrong_location', 'unregistered')))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.audit.session') or _('New')
        return super().create(vals_list)

    def action_start_audit(self):
        """Populates expected assets into audit lines."""
        self.ensure_one()
        domain = [('company_id', '=', self.company_id.id), ('state', 'in', ('open', 'paused'))]
        if self.target_location and self.target_location != 'All Locations':
            domain.append(('location_name', 'ilike', self.target_location.strip()))
        if self.category_id:
            domain.append(('category_id', '=', self.category_id.id))

        assets = self.env['account.asset.pro'].search(domain)
        lines = []
        for asset in assets:
            lines.append((0, 0, {
                'asset_id': asset.id,
                'barcode': asset.barcode or asset.code,
                'expected_location': asset.location_name,
                'status': 'pending',
            }))

        self.line_ids = lines
        self.state = 'in_progress'

    def action_scan_barcode(self):
        """Processes scanned barcode from laser scanner or mobile input."""
        self.ensure_one()
        scanned_code = (self.barcode_scan_input or '').strip()
        if not scanned_code:
            return True

        # Clear input field for next scan
        self.barcode_scan_input = False

        # Match existing audit line
        line = self.line_ids.filtered(lambda l: (l.barcode and l.barcode.strip() == scanned_code) or (l.asset_id and (l.asset_id.code == scanned_code or l.asset_id.serial_no == scanned_code)))
        if line:
            line = line[0]
            # Check location match
            if self.target_location and self.target_location != 'All Locations' and line.expected_location != self.target_location:
                line.status = 'wrong_location'
                line.scanned_location = self.target_location
            else:
                line.status = 'verified'
                line.scanned_location = line.expected_location or self.target_location
            line.scan_datetime = fields.Datetime.now()
            return True

        # Asset exists in database but not in expected session filter
        asset = self.env['account.asset.pro'].search([
            ('company_id', '=', self.company_id.id),
            '|', '|',
            ('barcode', '=', scanned_code),
            ('code', '=', scanned_code),
            ('serial_no', '=', scanned_code)
        ], limit=1)

        if asset:
            self.env['asset.audit.session.line'].create({
                'session_id': self.id,
                'asset_id': asset.id,
                'barcode': asset.barcode or asset.code,
                'expected_location': asset.location_name,
                'scanned_location': self.target_location or 'Audit Location',
                'status': 'wrong_location',
                'scan_datetime': fields.Datetime.now(),
                'notes': _('Asset was stationed in %s but scanned here.') % (asset.location_name or 'Unspecified')
            })
        else:
            # Unregistered barcode
            self.env['asset.audit.session.line'].create({
                'session_id': self.id,
                'barcode': scanned_code,
                'expected_location': 'Unknown',
                'scanned_location': self.target_location or 'Audit Location',
                'status': 'unregistered',
                'scan_datetime': fields.Datetime.now(),
                'notes': _('Unrecognized barcode tag scanned. Needs asset tagging.')
            })

        return True

    def action_complete_audit(self):
        """Finalizes audit session, marks un-scanned assets as missing, and updates asset master cards."""
        self.ensure_one()
        today = fields.Date.today()
        for line in self.line_ids:
            if line.status == 'pending':
                line.status = 'missing'

            if line.asset_id:
                line.asset_id.write({
                    'last_audit_date': today,
                    'last_audit_session_id': self.id,
                    'audit_status': line.status if line.status in ('verified', 'missing', 'wrong_location') else 'verified',
                })

        self.state = 'done'

    def action_reconcile_locations(self):
        """One-click batch update of asset locations to matched scanned location."""
        self.ensure_one()
        count = 0
        for line in self.line_ids.filtered(lambda l: l.status == 'wrong_location' and l.asset_id and l.scanned_location):
            line.asset_id.location_name = line.scanned_location
            line.status = 'verified'
            count += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Location Reconciled'),
                'message': _('Successfully updated physical locations for %s assets.') % count,
                'sticky': False,
            }
        }


class AssetAuditSessionLine(models.Model):
    _name = 'asset.audit.session.line'
    _description = 'Physical Asset Audit Line Item'
    _order = 'status, id'

    session_id = fields.Many2one('asset.audit.session', string='Audit Session', required=True, ondelete='cascade')
    asset_id = fields.Many2one('account.asset.pro', string='Fixed Asset', ondelete='set null')
    barcode = fields.Char(string='Scanned Barcode / QR')
    expected_location = fields.Char(string='Expected Location')
    scanned_location = fields.Char(string='Actual Scanned Location')
    scan_datetime = fields.Datetime(string='Scan Timestamp')
    notes = fields.Char(string='Auditor Notes / Discrepancy Reason')

    status = fields.Selection([
        ('pending', 'Pending Scan'),
        ('verified', 'Verified Present'),
        ('missing', 'Missing / Unaccounted'),
        ('wrong_location', 'Found in Wrong Location'),
        ('unregistered', 'Unregistered Tag'),
    ], string='Audit Verdict', default='pending', required=True)
