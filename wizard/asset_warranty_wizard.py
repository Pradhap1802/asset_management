from odoo import models, fields, api, _
from datetime import timedelta

class AssetWarrantyWizard(models.TransientModel):
    _name = 'asset.warranty.wizard'
    _description = 'Asset Warranty Expiry Wizard'

    days_ahead = fields.Integer(string="Days Ahead", default=30, help="Check warranties expiring within these many days")
    asset_ids = fields.Many2many('asset.management', string="Expiring Assets", compute="_compute_expiring_assets", store=False)

    @api.depends('days_ahead')
    def _compute_expiring_assets(self):
        for record in self:
            today = fields.Date.today()
            target_date = today + timedelta(days=record.days_ahead)
            
            domain = [
                ('expired_warranty_date', '!=', False),
                ('expired_warranty_date', '<=', target_date),
                ('status', 'not in', ('destroyed',))
            ]
            assets = self.env['asset.management'].search(domain)
            record.asset_ids = [(6, 0, assets.ids)]


    def action_close(self):
        """When closing the wizard, proceed to the main assets list anyway"""
        return self.env.ref('asset_management.action_assets').read()[0]
