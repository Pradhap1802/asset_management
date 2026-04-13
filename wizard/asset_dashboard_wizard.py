from odoo import models, fields, api

class AssetDashboardWizard(models.TransientModel):
    _name = 'asset.dashboard.wizard'
    _description = 'Asset Dashboard Drill-down Wizard'

    asset_type_id = fields.Many2one('asset.type', string="Asset Type", readonly=True)
    summary_line_ids = fields.One2many('asset.dashboard.wizard.line', 'wizard_id', string="Summary Lines")
    total_count = fields.Integer(string="Total Assets")
    total_value = fields.Float(string="Total Value")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def populate_summary_lines(self):
        for record in self:
            domain = [('asset_type_id', '=', record.asset_type_id.id)]
            if self.env.company.parent_id:
                domain.append(('company_id', 'in', self.env.companies.ids))
            
            assets = self.env['asset.management'].sudo().search(domain)
            
            # Group by Company and Asset Name
            summary_data = {}
            for asset in assets:
                key = (asset.company_id.id, asset.name)
                if key not in summary_data:
                    summary_data[key] = {
                        'count': 0, 
                        'orig_value': 0.0, 
                        'curr_value': 0.0,
                        'transfers': 0,
                        'maintenance': 0
                    }
                summary_data[key]['count'] += 1
                summary_data[key]['orig_value'] += asset.amount
                summary_data[key]['curr_value'] += asset.current_amount
                summary_data[key]['transfers'] += asset.transfer_count
                summary_data[key]['maintenance'] += asset.maintenance_count
            
            lines = []
            for (company_id, name), data in summary_data.items():
                lines.append((0, 0, {
                    'company_id': company_id,
                    'name': name,
                    'count': data['count'],
                    'original_value': data['orig_value'],
                    'current_value': data['curr_value'],
                    'transfer_count': data['transfers'],
                    'maintenance_count': data['maintenance'],
                }))
            
            record.write({
                'summary_line_ids': lines,
                'total_count': len(assets),
                'total_value': sum(assets.mapped('current_amount'))
            })

class AssetDashboardWizardLine(models.TransientModel):
    _name = 'asset.dashboard.wizard.line'
    _description = 'Asset Dashboard Summary Line'

    wizard_id = fields.Many2one('asset.dashboard.wizard', string="Wizard")
    company_id = fields.Many2one('res.company', string="Location / Branch")
    name = fields.Char(string="Asset Name")
    count = fields.Integer(string="Stock Count")
    original_value = fields.Float(string="Original Value")
    current_value = fields.Float(string="Current Value")
    transfer_count = fields.Integer(string="Transfers")
    maintenance_count = fields.Integer(string="Maintenance")
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
