# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

THEME_PRESETS = [
    ('emerald_aurora', 'Emerald Aurora (Nordic Teal & Fresh Mint)'),
    ('cyberpunk_neon', 'Cyberpunk Neon (Midnight & Electric Cyan)'),
    ('royal_velvet', 'Royal Velvet (Imperial Amethyst & Sovereign Gold)'),
    ('sunset_horizon', 'Sunset Horizon (Warm Tangerine & Amber Coral)'),
    ('pristine_paper', 'Pristine Paper (Pure Crisp White & Cobalt Blue)'),
    ('obsidian_luxe', 'Obsidian Luxe (Linear Monochromatic Black & Platinum)'),
    ('deep_oceanic', 'Deep Oceanic (Bermuda Maritime Navy & Seafoam Turquoise)'),
    ('crimson_apex', 'Crimson Apex (Executive Matte Burgundy & Scarlet)'),
    ('forest_zen', 'Forest Zen (Organic Bamboo Sage & Matcha Green)'),
    ('modern_slate', 'Modern Slate (Silicon Valley Slate & Electric Indigo)'),
]

PALETTE_DEFAULTS = {
    'emerald_aurora': {
        'navbar_bg': '#064E3B',
        'navbar_text': '#ECFDF5',
        'primary_color': '#10B981',
        'view_bg': '#F0FDF4',
        'card_bg': '#FFFFFF',
        'border_color': '#A7F3D0',
        'icon': '🌿',
        'desc': 'Refreshing Scandinavian teal with energizing mint highlights'
    },
    'cyberpunk_neon': {
        'navbar_bg': '#0B0F19',
        'navbar_text': '#00F0FF',
        'primary_color': '#00F0FF',
        'view_bg': '#070A10',
        'card_bg': '#0F172A',
        'border_color': '#FF007F',
        'icon': '⚡',
        'desc': 'High-contrast futuristic dark mode with neon cyan and magenta accents'
    },
    'royal_velvet': {
        'navbar_bg': '#3B0764',
        'navbar_text': '#FAF5FF',
        'primary_color': '#EAB308',
        'view_bg': '#FAF5FF',
        'card_bg': '#FFFFFF',
        'border_color': '#E9D5FF',
        'icon': '👑',
        'desc': 'Imperial deep amethyst canvas paired with sovereign gold touches'
    },
    'sunset_horizon': {
        'navbar_bg': '#C2410C',
        'navbar_text': '#FFF7ED',
        'primary_color': '#F97316',
        'view_bg': '#FFFBF5',
        'card_bg': '#FFFFFF',
        'border_color': '#FED7AA',
        'icon': '🌅',
        'desc': 'Warm sunrise terracotta with high-energy amber accents'
    },
    'pristine_paper': {
        'navbar_bg': '#1E40AF',
        'navbar_text': '#FFFFFF',
        'primary_color': '#2563EB',
        'view_bg': '#FFFFFF',
        'card_bg': '#FFFFFF',
        'border_color': '#E2E8F0',
        'icon': '📄',
        'desc': '100% pure crisp white paper views with cobalt blue precision'
    },
    'obsidian_luxe': {
        'navbar_bg': '#09090B',
        'navbar_text': '#FAFAFA',
        'primary_color': '#D97706',
        'view_bg': '#121215',
        'card_bg': '#18181B',
        'border_color': '#27272A',
        'icon': '💎',
        'desc': 'Linear-inspired obsidian black with mathematical 1px hairline borders'
    },
    'deep_oceanic': {
        'navbar_bg': '#0C4A6E',
        'navbar_text': '#F0F9FF',
        'primary_color': '#06B6D4',
        'view_bg': '#F0F9FF',
        'card_bg': '#FFFFFF',
        'border_color': '#BAE6FD',
        'icon': '🌊',
        'desc': 'Deep maritime ocean navy with glowing turquoise seafoam accents'
    },
    'crimson_apex': {
        'navbar_bg': '#881337',
        'navbar_text': '#FFF1F2',
        'primary_color': '#E11D48',
        'view_bg': '#FFF1F2',
        'card_bg': '#FFFFFF',
        'border_color': '#FECDD3',
        'icon': '🔥',
        'desc': 'Executive deep burgundy with commanding crimson button highlights'
    },
    'forest_zen': {
        'navbar_bg': '#14532D',
        'navbar_text': '#F7FEE7',
        'primary_color': '#65A30D',
        'view_bg': '#FDFBF7',
        'card_bg': '#FFFFFF',
        'border_color': '#D9F99D',
        'icon': '🎋',
        'desc': 'Calming organic sage with matcha moss and natural bamboo tones'
    },
    'modern_slate': {
        'navbar_bg': '#1E293B',
        'navbar_text': '#F8FAFC',
        'primary_color': '#6366F1',
        'view_bg': '#F8FAFC',
        'card_bg': '#FFFFFF',
        'border_color': '#CBD5E1',
        'icon': '🚀',
        'desc': 'Silicon Valley modern tech slate with electric indigo micro-accents'
    },
}


class OmniThemeConfig(models.Model):
    _name = 'omni.theme.config'
    _description = 'OmniTheme 10-in-1 Studio Configuration'
    _order = 'is_active desc, id desc'

    name = fields.Char(
        string='Configuration Name',
        required=True,
        default='OmniTheme Corporate Studio'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )
    is_active = fields.Boolean(
        string='Active Company Theme',
        default=True,
        help='Whether this theme profile is active for the company.'
    )
    theme_key = fields.Selection(
        selection=THEME_PRESETS,
        string='Active Theme Preset',
        default='emerald_aurora',
        required=True,
        help='Choose one of the 10 beautifully pre-crafted themes.'
    )
    allow_user_switching = fields.Boolean(
        string='Allow Personal User Toggles',
        default=True,
        help='If checked, individual users can switch themes via their top-right navbar toggle.'
    )
    navbar_bg = fields.Char(
        string='Navbar Background',
        default='#064E3B',
        help='Hex color for the main top navigation bar.'
    )
    navbar_text = fields.Char(
        string='Navbar Text Color',
        default='#ECFDF5',
        help='Hex color for navbar links, icons, and titles.'
    )
    primary_color = fields.Char(
        string='Primary Action Color',
        default='#10B981',
        help='Hex color for primary action buttons, active states, and highlights.'
    )
    view_bg = fields.Char(
        string='View Background Color',
        default='#F0FDF4',
        help='Hex color for the workspace view container.'
    )
    card_bg = fields.Char(
        string='Card / Sheet Background',
        default='#FFFFFF',
        help='Hex color for form sheets and kanban cards.'
    )
    border_color = fields.Char(
        string='Border / Divider Color',
        default='#A7F3D0',
        help='Hex color for dividing lines and card borders.'
    )
    font_family = fields.Selection([
        ('inter', 'Inter (Modern Tech / UI Standard)'),
        ('roboto', 'Roboto (Clean Geometric)'),
        ('poppins', 'Poppins (Sophisticated Display)'),
        ('system', 'System Native (San Francisco / Segoe UI)')
    ], string='Typography Family', default='inter', required=True)

    button_border_radius = fields.Selection([
        ('rounded_8', 'Modern Rounded (8px)'),
        ('pill_20', 'Curved Pill (20px)'),
        ('sharp_4', 'Sharp Precision (4px)')
    ], string='Button Corner Geometry', default='rounded_8', required=True)

    @api.onchange('theme_key')
    def _onchange_theme_key(self):
        """Auto-populate hex colors when switching presets in form."""
        if self.theme_key and self.theme_key in PALETTE_DEFAULTS:
            defaults = PALETTE_DEFAULTS[self.theme_key]
            self.navbar_bg = defaults['navbar_bg']
            self.navbar_text = defaults['navbar_text']
            self.primary_color = defaults['primary_color']
            self.view_bg = defaults['view_bg']
            self.card_bg = defaults['card_bg']
            self.border_color = defaults['border_color']

    def action_apply_theme(self):
        """Make this profile active for the current company and enforce default palette."""
        self.ensure_one()
        # Deactivate other configs for this company
        other_configs = self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('is_active', '=', True)
        ])
        other_configs.write({'is_active': False})
        self.is_active = True
        self._onchange_theme_key()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def get_ten_themes_meta(self):
        """Returns metadata for all 10 themes for UI toggles and systray switcher."""
        theme_list = []
        for key, name in THEME_PRESETS:
            palette = PALETTE_DEFAULTS.get(key, {})
            theme_list.append({
                'key': key,
                'name': name.split(' (')[0],
                'subtitle': name.split(' (')[1].replace(')', '') if ' (' in name else '',
                'navbar_bg': palette.get('navbar_bg', '#1E293B'),
                'navbar_text': palette.get('navbar_text', '#FFFFFF'),
                'primary_color': palette.get('primary_color', '#6366F1'),
                'view_bg': palette.get('view_bg', '#FFFFFF'),
                'card_bg': palette.get('card_bg', '#FFFFFF'),
                'border_color': palette.get('border_color', '#CBD5E1'),
                'icon': palette.get('icon', '🎨'),
                'desc': palette.get('desc', '')
            })
        return theme_list

    @api.model
    def get_user_active_theme_config(self):
        """Returns the active theme for current user: personal preference or company default."""
        user = self.env.user
        theme_key = user.omni_theme_selection or 'emerald_aurora'
        company_config = self.search([
            ('company_id', '=', self.env.company.id),
            ('is_active', '=', True)
        ], limit=1)

        # If user switching is disabled by admin, use company config
        if company_config and not company_config.allow_user_switching:
            theme_key = company_config.theme_key

        palette = PALETTE_DEFAULTS.get(theme_key, PALETTE_DEFAULTS['emerald_aurora'])
        font_family = company_config.font_family if company_config else 'inter'
        button_radius = company_config.button_border_radius if company_config else 'rounded_8'

        radius_px = '8px'
        if button_radius == 'pill_20':
            radius_px = '20px'
        elif button_radius == 'sharp_4':
            radius_px = '4px'

        return {
            'theme_key': theme_key,
            'name': [t[1] for t in THEME_PRESETS if t[0] == theme_key][0] if theme_key in dict(THEME_PRESETS) else 'Emerald Aurora',
            'navbar_bg': palette['navbar_bg'],
            'navbar_text': palette['navbar_text'],
            'primary_color': palette['primary_color'],
            'view_bg': palette['view_bg'],
            'card_bg': palette['card_bg'],
            'border_color': palette['border_color'],
            'font_family': font_family,
            'button_radius': radius_px,
            'allow_user_switching': company_config.allow_user_switching if company_config else True,
            'all_themes': self.get_ten_themes_meta()
        }
