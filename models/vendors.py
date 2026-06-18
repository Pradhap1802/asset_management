from odoo import models, fields

class AssetVendor(models.Model):
    _name = 'asset.vendor'
    _description = 'Asset Vendor'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    # Basic Information
    name = fields.Char(string="Name", required=True, help="Official registered name of the vendor company")
    address = fields.Char(string="Primary Address", help="Main business address of the vendor")
    location = fields.Char(string="Service Area", help="Geographic regions where the vendor operates or provides services")
    
    # Contact Information
    seller = fields.Char(string="Primary Contact", help="Name and position of the main point of contact")
    contact_phone = fields.Char(string="Contact Phone", help="Primary phone number for vendor communication")
    contact_email = fields.Char(string="Contact Email", help="Primary email address for vendor communication")
    
    # Service Offerings
    additional_services = fields.Boolean(string="Additional Services", help="Other relevant services offered by the vendor")
    repair_service = fields.Boolean(string="Repair Services", help="Indicates if the vendor offers repair services (Yes/No)")
    maintenance_service = fields.Boolean(string="Maintenance Services", help="Indicates if the vendor provides maintenance services (Yes/No)")
    
    # Link back to the Odoo contact (res.partner)
    partner_id = fields.Many2one(
        'res.partner',
        string="Contact",
        readonly=True,
        copy=False,
        help="Linked Odoo contact record that auto-created this vendor"
    )