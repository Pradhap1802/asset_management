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
            domain = [('asset_type_id', '=', record.asset_type_id.id), ('asset_status', '!=', 'expired')]
            if self.env.company.parent_id:
                domain.append(('company_id', 'in', self.env.companies.ids))
            
            assets = self.env['asset.management'].sudo().search(domain)
            
            lines = []
            for asset in assets:
                product_name = asset.product_id.name if asset.product_id else asset.name
                depreciated_amount = asset.amount - asset.current_amount
                # Depreciation method info from asset type
                dep_method = ''
                dep_rate_display = ''
                useful_life = ''
                if asset.asset_type_id:
                    at = asset.asset_type_id
                    if at.depreciation_method == 'fix':
                        dep_method = 'Straight Line (SLM)'
                    else:
                        dep_method = 'Written Down Value (WDV)'
                    if at.depreciation_frequency == 'yearly':
                        dep_rate_display = 'Yearly'
                    elif at.depreciation_frequency == 'monthly':
                        dep_rate_display = 'Monthly'
                    else:
                        dep_rate_display = 'Daily'
                    if at.maximum_depreciation_entries:
                        if at.depreciation_frequency == 'yearly':
                            useful_life = '%d Years' % at.maximum_depreciation_entries
                        elif at.depreciation_frequency == 'monthly':
                            useful_life = '%d Months' % at.maximum_depreciation_entries
                        else:
                            useful_life = '%d Days' % at.maximum_depreciation_entries

                lines.append((0, 0, {
                    'company_id': asset.company_id.id,
                    'name': product_name,
                    'asset_ref': asset.name,
                    'asset_status': asset.asset_status or 'active',
                    'count': asset.initial_stock,
                    'original_value': asset.amount,
                    'current_value': asset.current_amount,
                    'depreciated_amount': depreciated_amount,
                    'transfer_count': asset.transfer_count,
                    'maintenance_count': asset.maintenance_count,
                    'maintenance_cost': asset.total_maintenance_amount,
                    'depreciation_method': dep_method,
                    'depreciation_frequency': dep_rate_display,
                    'useful_life': useful_life,
                    'warranty_expiry': asset.expired_warranty_date,
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
    asset_ref = fields.Char(string="Reference")
    asset_status = fields.Selection([
        ('active', 'Active'),
        ('maintenance_due', 'Maintenance Due'),
        ('expired', 'Expired/Scrap')
    ], string="Status")
    count = fields.Integer(string="Stock Count")
    original_value = fields.Float(string="Purchase Value")
    current_value = fields.Float(string="Current Book Value")
    depreciated_amount = fields.Float(string="Accumulated Depreciation")
    transfer_count = fields.Integer(string="Transfers")
    maintenance_count = fields.Integer(string="Maintenance")
    maintenance_cost = fields.Float(string="Maintenance Cost")
    depreciation_method = fields.Char(string="Depreciation Method")
    depreciation_frequency = fields.Char(string="Frequency")
    useful_life = fields.Char(string="Useful Life")
    warranty_expiry = fields.Date(string="Warranty Expiry")
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
