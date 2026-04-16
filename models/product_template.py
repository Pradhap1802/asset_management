from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    can_be_asset = fields.Boolean(
        string="Create Asset on Bill Confirm",
        default=False,
        help="If checked, confirming a vendor bill with this product will "
             "automatically create an Asset Management record.",
    )
