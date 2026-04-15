from odoo import models, fields

class StockMove(models.Model):
    _inherit = 'stock.move'

    asset_warranty_date = fields.Date(string="Asset Warranty Expiry", help="Warranty Expiry Date for the Asset Management tracking")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    asset_warranty_date = fields.Date(string="Asset Warranty Expiry", help="Warranty Expiry Date for the Asset Management tracking", related='move_id.asset_warranty_date', readonly=False)

