from odoo import models, fields

class StockScrap(models.Model):
    _inherit = 'stock.scrap'

    asset_disposal_id = fields.Many2one(
        'asset.disposal',
        string="Asset Disposal",
        ondelete='set null',
        help="The asset disposal record that triggered this scrap",
    )
