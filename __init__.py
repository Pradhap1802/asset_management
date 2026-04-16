from . import models
from . import wizard
from . import report


def _post_init_hook(env):
    """Load Enterprise-specific views if account_asset module is installed."""
    module = env['ir.module.module'].search([
        ('name', '=', 'account_asset'),
        ('state', '=', 'installed'),
    ], limit=1)
    if module:
        from odoo.tools import convert_file
        convert_file(
            env, 'asset_management',
            'views/account_asset_views.xml',
            idref={}, mode='init', noupdate=False,
        )