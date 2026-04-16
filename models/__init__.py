from . import asset_management
from . import vendors
from . import stock_movement_report
try:
    from . import account_asset
except (ImportError, Exception):
    pass
from . import res_partner
from . import account_move
from . import stock_move
from . import product_template