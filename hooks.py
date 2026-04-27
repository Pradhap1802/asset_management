import logging

_logger = logging.getLogger(__name__)


def post_migrate_resync_serials(env):
    """
    Post-migrate hook: Re-sync asset_serial_number on all account.asset records
    that are missing a serial number.  Runs automatically on every module upgrade
    so that assets created before the positional serial fix are corrected.
    """
    _logger.info("asset_management: re-syncing serial numbers on existing accounting assets…")

    # Only target non-model assets with a blank serial number
    assets = env['account.asset'].search([
        ('state', '!=', 'model'),
        ('asset_serial_number', '=', False),
    ])

    if not assets:
        _logger.info("asset_management: no assets with missing serial numbers found.")
        return

    _logger.info("asset_management: found %d asset(s) to re-sync.", len(assets))
    assets._sync_to_asset_management()
    _logger.info("asset_management: serial number re-sync complete.")
