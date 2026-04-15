from odoo import models, fields, api

class AssetDashboardWizard(models.TransientModel):
    _name = 'asset.dashboard.wizard'
    _description = 'Asset Dashboard Drill-down Wizard'

    asset_type_id = fields.Many2one('asset.type', string="Asset Type", readonly=True)
    summary_line_ids = fields.One2many('asset.dashboard.wizard.line', 'wizard_id', string="Summary Lines")
    maintenance_line_ids = fields.One2many('asset.dashboard.wizard.maintenance', 'wizard_id', string="Maintenance Records")
    total_count = fields.Integer(string="Total Assets")
    total_value = fields.Float(string="Total Value")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    def populate_summary_lines(self):
        for record in self:
            domain = [('asset_type_id', '=', record.asset_type_id.id)]
            if self.env.company.parent_id:
                domain.append(('company_id', 'in', self.env.companies.ids))
            
            assets = self.env['asset.management'].sudo().search(domain)
            
            # Group by Company and Product Name
            summary_data = {}
            for asset in assets:
                # Use product name instead of asset reference
                product_name = asset.product_id.name if asset.product_id else asset.name
                key = (asset.company_id.id, product_name)
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
            for (company_id, product_name), data in summary_data.items():
                depreciated_amount = data['orig_value'] - data['curr_value']
                lines.append((0, 0, {
                    'company_id': company_id,
                    'name': product_name,
                    'count': data['count'],
                    'original_value': data['orig_value'],
                    'current_value': data['curr_value'],
                    'depreciated_amount': depreciated_amount,
                    'transfer_count': data['transfers'],
                    'maintenance_count': data['maintenance'],
                }))
            
            # Collect all maintenance records for all assets
            maintenance_lines = []
            for asset in assets:
                for maintenance in asset.maintenance_ids:
                    maintenance_lines.append((0, 0, {
                        'asset_id': asset.id,
                        'asset_name': asset.product_id.name if asset.product_id else asset.name,
                        'maintenance_date': maintenance.assign_date,
                        'completion_date': maintenance.return_date,
                        'maintenance_vendor': maintenance.maintenance_vendor_id.name if maintenance.maintenance_vendor_id else '',
                        'maintenance_amount': maintenance.maintenance_amount,
                        'maintenance_status': maintenance.maintenance_status,
                    }))
            
            record.write({
                'summary_line_ids': lines,
                'maintenance_line_ids': maintenance_lines,
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
    depreciated_amount = fields.Float(string="Depreciated Amount")
    transfer_count = fields.Integer(string="Transfers")
    maintenance_count = fields.Integer(string="Maintenance")
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')


class AssetDashboardWizardMaintenance(models.TransientModel):
    _name = 'asset.dashboard.wizard.maintenance'
    _description = 'Asset Dashboard Maintenance Line'

    wizard_id = fields.Many2one('asset.dashboard.wizard', string="Wizard")
    asset_id = fields.Many2one('asset.management', string="Asset")
    asset_name = fields.Char(string="Asset Name")
    maintenance_date = fields.Date(string="Maintenance Date")
    completion_date = fields.Date(string="Completion Date")
    maintenance_vendor = fields.Char(string="Vendor")
    maintenance_amount = fields.Float(string="Amount")
    maintenance_status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    ], string="Status")
