from odoo import models, fields, api

class AssetDashboardWizard(models.TransientModel):
    _name = 'asset.dashboard.wizard'
    _description = 'Asset Dashboard Drill-down Wizard'

    asset_type_id = fields.Many2one('asset.type', string="Asset Type", readonly=True)
    asset_ids = fields.Many2many('asset.management', string="Assets", compute="_compute_assets", store=False)
    total_count = fields.Integer(string="Total Assets", compute="_compute_assets")
    total_value = fields.Float(string="Total Value", compute="_compute_assets")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    @api.depends('asset_type_id')
    def _compute_assets(self):
        for record in self:
            domain = [('asset_type_id', '=', record.asset_type_id.id)]
            # Respect multi-company hierarchy: Main sees all, branches see only themselves
            if self.env.company.parent_id:
                domain.append(('company_id', 'in', self.env.companies.ids))
            
            assets = self.env['asset.management'].search(domain)
            record.asset_ids = [(6, 0, assets.ids)]
            record.total_count = len(assets)
            record.total_value = sum(assets.mapped('current_amount'))
