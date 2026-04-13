from odoo import models, fields

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    asset_serial_number = fields.Char(string="Asset Serial / Barcode", help="Serial Number or Barcode for the Asset Management tracking")
    asset_warranty_date = fields.Date(string="Asset Warranty Expiry", help="Warranty Expiry Date for the Asset Management tracking")
