from odoo import models, fields, api, _, exceptions
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta


class Asset(models.Model):
    _name = 'asset.management'
    _description = 'Asset Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Asset Information
    name = fields.Char(string="Asset Reference", required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    barcode = fields.Char(string="Barcode", copy=False, help="Barcode for asset identification and scanning")
    serial_number_ids = fields.One2many('asset.serial.number', 'asset_id', string="Serial Numbers")
    product_id = fields.Many2one('product.product', string="Associated Product", help="Select the product used in this asset from available options")
    asset_type_id = fields.Many2one('asset.type', string="Asset Type", help="Classification of the asset (e.g., Equipment, Vehicle, Building)")
    
    initial_stock = fields.Integer(string="Initial Stock", default=0,
                                  help="Original quantity purchased / received for this asset")
    current_stock = fields.Integer(string="Current Stock", default=0, store=True,
                                  help="Current available quantity at this branch")
    active_transfers = fields.Integer(string="Active Transfers", compute='_compute_active_transfers', store=True,
                                     help="Number of assets currently assigned to users")
    
    # Depreciation Settings
    depreciation_apply = fields.Boolean(string="Enable Depreciation", help="Check to apply depreciation calculations for this asset")
    
    # Vendor and Purchase Information
    expired_warranty_date = fields.Date(string="Expired Warranty Date")
    vendor_id = fields.Many2one('asset.vendor', string="Associated Vendor", help="Select the vendor or supplier of this asset")
    invoice_date = fields.Date(string="Invoice Date", help="Date when the asset was purchased or acquired")
    amount = fields.Float(string="Purchase Price", help="Initial cost of acquiring the asset")
    
    # Lifecycle Dates
    capitalization_date = fields.Date(string="Capitalization Date", help="Date when the asset was capitalized in the books")
    end_of_life_date = fields.Date(string="End of Life Date", help="Expected or actual end of life date for the asset")
    last_maintenance_date = fields.Date(string="Last Maintenance Date", compute="_compute_last_maintenance_date_field", store=True, help="Date of the last completed maintenance")
    next_maintenance_due = fields.Date(string="Next Maintenance Due", compute="_compute_next_maintenance_due", store=True, help="Calculated next maintenance due date")
    
    # Asset Status Indicator
    asset_status = fields.Selection([
        ('active', 'Active'),
        ('maintenance_due', 'Maintenance'),
        ('expired', 'Expired/Scrap')
    ], string="Asset Status", default='active', tracking=True, help="Current lifecycle status of the asset")
    
    # Computed Financial Fields
    current_amount = fields.Float(string="Current Book Value", compute="_compute_current_amount", help="Current value of the asset after depreciation (Read-only)")
    total_depreciation_amount = fields.Float(string="Accumulated Depreciation",
                                             compute='_compute_total_depreciation_amount', store=True, help="Total depreciation applied to the asset to date (Read-only)")
    total_maintenance_amount = fields.Float(string="Total Maintenance Cost",
                                            compute='_compute_total_maintenance_amount', store=True, help="Sum of all maintenance expenses for this asset (Read-only)")
    total_downtime_days = fields.Integer(string="Total Downtime (Days)",
                                         compute='_compute_total_downtime_days', store=True, help="Total downtime days across all maintenance entries")

    # Related Documents and Entries
    document_ids = fields.Many2many('ir.attachment', string="Asset Documentation", help="Upload multiple documents related to the asset (e.g., Warranty,Invoice)")
    tag_ids = fields.Many2many('asset.tag', string='Tags', help="Categorize assets with tags for easier filtering and organization")
    transfer_ids = fields.One2many('asset.transfer.entry', 'asset_id', string="Transfer Entries")
    maintenance_ids = fields.One2many('asset.maintenance.entry', 'asset_id', string="Maintenance Entries")
    depreciation_ids = fields.One2many('asset.depreciation.entry', 'asset_id', string="Depreciation Entries")
    disposal_ids = fields.One2many('asset.disposal', 'asset_id', string="Disposal Records")
    
    # Additional Information
    last_depreciation_date = fields.Date(string="Last Depreciation Date", help="Last Depreciation Entry Date", compute='_compute_last_depreciation_date', store=True)
    transfer_count = fields.Integer(string='Asset Transfer History',
                                    compute='_compute_all_count', store=True)
    maintenance_count = fields.Integer(string='Maintenance Records',
                                       compute='_compute_all_count', store=True)
    depreciation_count = fields.Integer(string='Depreciation Count',
                                        compute='_compute_all_count', store=True)
    disposal_count = fields.Integer(string='Disposal Records',
                                    compute='_compute_all_count', store=True)
    invoice_id = fields.Many2one('account.move', string="Associated Invoice")
    months_left = fields.Integer(string='Months Left',)
    assigned_user = fields.Char(string="Assigned User", compute='_compute_assigned_user',
                                store=True)
    assign_by = fields.Char(string="Assigned By", compute='_compute_assigned_user',
                                store=True)
    remaining_warranty = fields.Char(string="Remaining Warranty",
                                     compute="_compute_months_left", store=True)
    warranty_status = fields.Char(string='Warranty Status')
    # Link back to the Odoo Enterprise accounting asset
    accounting_asset_id = fields.Many2one(
        'account.asset',
        string="Accounting Asset",
        readonly=True,
        copy=False,
        help="Linked Odoo Enterprise Accounting Asset record"
    )
    # Vendor from the linked invoice (res.partner)
    vendor_partner_id = fields.Many2one(
        'res.partner',
        string="Invoice Vendor",
        readonly=True,
        copy=False,
        help="Vendor/Supplier from the linked accounting invoice"
    )
    # Company / Branch that owns this asset
    company_id = fields.Many2one(
        'res.company',
        string="Company / Branch",
        default=lambda self: self.env.company,
        copy=False,
        help="The company or branch for which this asset was created (e.g., Salem Branch)"
    )
    

    @api.depends('transfer_ids', 'transfer_ids.status', 'transfer_ids.stock_qty')
    def _compute_active_transfers(self):
        for record in self:
            # Sum quantities in 'assigned' (employee-assigned) transfers for display
            assigned_transfers = record.transfer_ids.filtered(lambda t: t.status == 'assigned')
            record.active_transfers = sum(assigned_transfers.mapped('stock_qty'))

    @api.onchange('initial_stock')
    def _onchange_initial_stock(self):
        """When initial_stock is set on a new record, mirror it to current_stock."""
        for record in self:
            if not record.id:  # Only for new unsaved records
                record.current_stock = record.initial_stock

    # Compute methods
    @api.depends('expired_warranty_date')
    def _compute_months_left(self):
        today = fields.Date.today()
        for record in self:
            if record.expired_warranty_date:
                if record.expired_warranty_date < today:
                    record.remaining_warranty = 'Expired'
                    record.warranty_status = 'expired'

                elif record.expired_warranty_date == today:
                    record.remaining_warranty = 'Today'
                    record.warranty_status = 'danger'

                else:
                    rd = relativedelta(record.expired_warranty_date, today)
                    total_months = rd.years * 12 + rd.months + (
                                rd.days / 30)  # Approximate

                    if total_months > 6:
                        record.warranty_status = 'success'
                    elif 3 <= total_months <= 6:
                        record.warranty_status = 'warning'
                    else:
                        record.warranty_status = 'danger'
                    years = rd.years
                    months = rd.months
                    days = rd.days

                    parts = []
                    if years > 0:
                        parts = [f"{years} year{'s' if years > 1 else ''}"]
                    elif months > 0:
                        parts = [f"{months} month{'s' if months > 1 else ''}"]
                    elif days > 0:
                        parts = [f"{days} day{'s' if days > 1 else ''}"]
                    
                       
                    print("parts : ", parts)
                    record.remaining_warranty = ', '.join(parts)

            else:
                record.remaining_warranty = 'No warranty'
                record.warranty_status = 'expired'

    @api.depends('transfer_ids')
    def _compute_assigned_user(self):
        for record in self:
            # Check if there are any transfer entries
            if record.transfer_ids:
                # Retrieve the most recent transfer entry based on 'assign_date'
                last_transfer = record.transfer_ids[-1]
                if last_transfer:
                    # Get the user who assigned the asset in the last transfer
                    record.assigned_user = last_transfer.transfer_employee_id.name
                    record.assign_by = last_transfer.assign_by.id
                else:
                    record.assigned_user = ''
                    record.assign_by = ''
            else:
                record.assigned_user = ''
                record.assign_by = ''

    @api.depends('maintenance_ids.return_date')
    def _compute_next_maintenance_due(self):
        """Calculate next maintenance due date based on last maintenance + 90 days"""
        for record in self:
            if record.maintenance_ids:
                # Get the last completed maintenance
                completed_maintenance = record.maintenance_ids.filtered(lambda m: m.maintenance_status == 'completed')
                if completed_maintenance:
                    last_maintenance = max(completed_maintenance, key=lambda m: m.return_date)
                    if last_maintenance.return_date:
                        # Add 90 days for next maintenance
                        record.next_maintenance_due = last_maintenance.return_date + timedelta(days=90)
                    else:
                        record.next_maintenance_due = False
                else:
                    record.next_maintenance_due = False
            else:
                record.next_maintenance_due = False

    @api.depends('maintenance_ids.return_date', 'maintenance_ids.maintenance_status')
    def _compute_last_maintenance_date_field(self):
        """Get the date of the last completed maintenance"""
        for record in self:
            completed = record.maintenance_ids.filtered(
                lambda m: m.maintenance_status == 'completed' and m.return_date
            )
            if completed:
                record.last_maintenance_date = max(completed.mapped('return_date'))
            else:
                record.last_maintenance_date = False

    @api.depends('transfer_ids', 'maintenance_ids', 'depreciation_ids.state', 'disposal_ids')
    def _compute_all_count(self):
        for record in self:
            record.transfer_count = len(record.transfer_ids)
            record.maintenance_count = len(record.maintenance_ids)
            record.depreciation_count = len(record.depreciation_ids.filtered(lambda d: d.state in ('posted', False)))
            record.disposal_count = len(record.disposal_ids)

    @api.depends('amount',)
    def _compute_current_amount(self):
        for record in self:
            record.current_amount = record.amount - record.total_depreciation_amount

    @api.depends('depreciation_ids.depreciation_amount', 'depreciation_ids.state')
    def _compute_total_depreciation_amount(self):
        for record in self:
            posted_entries = record.depreciation_ids.filtered(lambda d: d.state in ('posted', False))
            record.total_depreciation_amount = sum(posted_entries.mapped('depreciation_amount'))

    @api.depends('depreciation_ids.entry_date', 'depreciation_ids.state')
    def _compute_last_depreciation_date(self):
        for record in self:
            posted_entries = record.depreciation_ids.filtered(lambda d: d.state in ('posted', False) and d.entry_date)
            if posted_entries:
                record.last_depreciation_date = max(posted_entries.mapped('entry_date'))
            else:
                record.last_depreciation_date = False

    @api.depends('maintenance_ids.maintenance_amount')
    def _compute_total_maintenance_amount(self):
        for record in self:
            record.total_maintenance_amount = sum(record.maintenance_ids.mapped('maintenance_amount'))

    @api.depends('maintenance_ids.downtime_days')
    def _compute_total_downtime_days(self):
        for record in self:
            record.total_downtime_days = sum(record.maintenance_ids.mapped('downtime_days'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('asset.management') or 'New'
            # Mirror initial_stock → current_stock when creating a new asset
            # (unless current_stock is explicitly provided, e.g. from a branch split)
            if 'initial_stock' in vals and 'current_stock' not in vals:
                vals['current_stock'] = vals['initial_stock']
        return super(Asset, self).create(vals_list)

    def write(self, vals):
        """Auto-create a disposal record when asset_status is set to 'expired'."""
        # Capture which assets are NOT yet expired before the write
        previously_not_expired = self.filtered(lambda a: a.asset_status != 'expired')

        res = super(Asset, self).write(vals)

        if vals.get('asset_status') == 'expired':
            for asset in previously_not_expired:
                # Only create if no disposal record exists yet
                if not asset.disposal_ids:
                    self.env['asset.disposal'].create({
                        'asset_id': asset.id,
                        'disposal_date': fields.Date.today(),
                        'disposal_method': 'scrap',
                        'book_value_at_disposal': asset.current_amount,
                        'state': 'draft',
                    })
        return res

    def generate_depreciation_entries(self):
        """Generate depreciation entries with value subtraction."""
        assets = self.search(
            [('depreciation_apply', '=', True)])

        for asset in assets:
            # Check if the maximum number of depreciation entries has been reached
            existing_entries_count = self.env['asset.depreciation.entry'].search_count(
                [('asset_id', '=', asset.id),('create_uid', '=', 1)])
            max_entries = asset.asset_type_id.maximum_depreciation_entries

            if max_entries and existing_entries_count >= max_entries:
                continue  # Skip this asset if the maximum number of entries has been reached

            # Determine the starting date for depreciation
            start_date = asset.last_depreciation_date if asset.last_depreciation_date else asset.invoice_date
            if not start_date:
                continue  # Skip if no valid starting date

            # Calculate next depreciation date
            if asset.asset_type_id.depreciation_frequency == 'yearly':
                next_depreciation_date = start_date + relativedelta(
                    years=asset.asset_type_id.depreciation_start_delay)
            elif asset.asset_type_id.depreciation_frequency == 'monthly':
                next_depreciation_date = start_date + relativedelta(
                    months=asset.asset_type_id.depreciation_start_delay)
            elif asset.asset_type_id.depreciation_frequency == 'days':
                next_depreciation_date = start_date + timedelta(
                    days=asset.asset_type_id.depreciation_start_delay)
            else:
                continue  # Invalid depreciation type

            # Check if depreciation needs to be applied today
            if next_depreciation_date > datetime.today().date():
                continue  # Skip if next depreciation date is in the future

            # Determine the depreciation amount and subtract it from the value
            if asset.asset_type_id.depreciation_method == 'fix':
                depreciation_amount = asset.asset_type_id.depreciation_rate
            elif asset.asset_type_id.depreciation_method == 'percentage':
                base_amount = asset.amount if asset.asset_type_id.depreciation_basis == 'real_value' else asset.current_amount
                depreciation_amount = (
                                                  base_amount * asset.asset_type_id.depreciation_rate) / 100
            else:
                continue  # Invalid depreciation value type

            # Subtract the depreciation amount from the asset's value
            if asset.asset_type_id.depreciation_basis == 'real_value':
                asset.amount -= depreciation_amount
            else:
                asset.total_depreciation_amount -= depreciation_amount

            # Update the last depreciation date and create an entry in the depreciation model
            asset.last_depreciation_date = next_depreciation_date

            # Create a depreciation entry in the 'asset.depreciation' model
            self.env['asset.depreciation.entry'].create({
                'asset_id': asset.id,
                'created_by': self.env.uid,
                'depreciation_amount': depreciation_amount,
                'entry_date': datetime.today().date(),
                'bill_id': asset.invoice_id.id if asset.invoice_id else False,
            })

            print(
                f"Depreciation Entry Created for {asset.name}: {depreciation_amount} deducted on {next_depreciation_date}"
            )

    def action_open_label_layout(self):
        """Open the label layout wizard for printing asset labels"""
        action = self.env['ir.actions.act_window']._for_xml_id('asset_management.action_open_label_layout')
        action['context'] = {'default_asset_ids': self.ids}
        return action


class AssetTag(models.Model):
    _name = 'asset.tag'
    _description = 'Asset Tag'

    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color Index')
    
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists!"),
    ]


class AssetSerialNumber(models.Model):
    _name = 'asset.serial.number'
    _description = 'Asset Serial Number'
    _rec_name = 'name'

    name = fields.Char(string="Serial Number", required=True)
    asset_id = fields.Many2one('asset.management', string="Asset", required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string="Branch", related='asset_id.company_id', store=True, readonly=True)

    _sql_constraints = [
        ('unique_serial', 'unique(name)', 'Serial number must be unique!'),
    ]


class AssetTransferEntry(models.Model):
    _name = 'asset.transfer.entry'
    _description = 'Asset Transfer Entry'

    # Fields for tracking asset transfers
    asset_id = fields.Many2one('asset.management', string="Asset Reference", help="Choose the asset for which the transfer is being recorded")
    product_id = fields.Many2one('product.product', string="Product", related='asset_id.product_id', store=True, readonly=True)
    serial_number_ids = fields.Many2many(
        'asset.serial.number',
        'asset_transfer_serial_rel',
        'transfer_id',
        'serial_id',
        string="Serial Numbers",
        help="Select the serial numbers being transferred (one per unit)"
    )
    transfer_employee_id = fields.Many2one('hr.employee', string="Assigned To", help="Employee who is receiving or has received the asset")
    assign_date = fields.Date(string="Assign Date", help="Date when the asset was assigned to the employee")
    assign_by = fields.Many2one('res.users', string="Assign By", default=lambda self: self.env.user, help="Person responsible for assigning the asset")
    return_date = fields.Date(string="Return Date", help="Date when the asset was returned by the employee")
    status = fields.Selection([
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('under_maintenance', 'Under Maintenance')
    ], string="Status", help="Current status of the asset transfer")
    transfer_code = fields.Char(string="Transfer Code", copy=False, readonly=True, 
                               default=lambda self: _('New'), help="Unique identifier for this transfer")
    stock_qty = fields.Integer(string="Quantity", default=1, 
                              help="Quantity of assets being transferred (for multiple assets)")
    
    from_branch_id = fields.Many2one('res.company', string="From Branch", help="Original branch/company the asset is transferred from", default=lambda self: self.env.company)
    to_branch_id = fields.Many2one('res.company', string="To Branch", help="Destination branch/company the asset is transferred to")
    
    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        if self.asset_id and self.asset_id.company_id:
            self.from_branch_id = self.asset_id.company_id.id
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create to generate transfer code and handle branch stock updates."""
        for vals in vals_list:
            if vals.get('transfer_code', 'New') == 'New':
                vals['transfer_code'] = self.env['ir.sequence'].next_by_code('asset.transfer.entry') or 'New'

            if vals.get('asset_id') and vals.get('to_branch_id'):
                asset = self.env['asset.management'].browse(vals['asset_id'])
                qty = vals.get('stock_qty', 1)
                if qty <= 0:
                    raise exceptions.ValidationError(_("Transfer quantity must be greater than zero."))
                if asset.current_stock < qty:
                    raise exceptions.ValidationError(
                        _("Cannot transfer %d unit(s): only %d currently in stock.") % (qty, asset.current_stock)
                    )
            elif vals.get('asset_id') and vals.get('status') == 'assigned':
                asset = self.env['asset.management'].browse(vals['asset_id'])
                qty = vals.get('stock_qty', 1)
                if qty <= 0:
                    raise exceptions.ValidationError(_("Transfer quantity must be greater than zero."))
                if asset.current_stock < qty:
                    raise exceptions.ValidationError(_("Cannot assign this asset: Insufficient stock available."))

        records = super(AssetTransferEntry, self).create(vals_list)

        # Branch Transfer Logic
        for record in records:
            if (
                record.to_branch_id
                and record.asset_id.company_id != record.to_branch_id
            ):
                self._do_branch_transfer(record)

        return records

    def _do_branch_transfer(self, record):
        """Handle stock updates when an asset is transferred to another branch.

        Source branch (e.g., AVR):
            - initial_stock  → UNCHANGED  (reflects what was purchased at AVR)
            - current_stock  → decremented by transferred qty
              e.g. 12 → 7 after sending 5 out

        Destination branch (e.g., AVR Salem) — new asset record:
            - initial_stock  → 0  (nothing was purchased at AVR Salem)
            - current_stock  → equals the transferred qty (e.g. 5)
        """
        asset = record.asset_id
        qty = record.stock_qty

        if qty <= 0:
            raise exceptions.ValidationError(_(
                "Transfer quantity must be greater than zero."
            ))
        if qty > asset.current_stock:
            raise exceptions.ValidationError(_(
                "Cannot transfer %d unit(s): only %d currently in stock."
            ) % (qty, asset.current_stock))

        # Validate: number of serial numbers must not exceed qty
        if record.serial_number_ids and len(record.serial_number_ids) > qty:
            raise exceptions.ValidationError(_(
                "You selected %d serial number(s) but the transfer quantity is %d. "
                "Please match them."
            ) % (len(record.serial_number_ids), qty))

        # --- Source: reduce current_stock only; initial_stock stays as-is ---
        asset.sudo().write({'current_stock': asset.current_stock - qty})

        # --- Destination: new asset record at the target branch ---
        #   initial_stock = 0  → nothing was purchased/received at this branch
        #   current_stock = qty → the units that just arrived
        new_asset = asset.copy({
            'name': 'New',
            'company_id': record.to_branch_id.id,
            'initial_stock': 0,        # No purchase happened at destination
            'current_stock': qty,      # Received quantity
            'transfer_ids': False,
            'maintenance_ids': False,
            'depreciation_ids': False,
            'serial_number_ids': False,
        })

        # Move selected serial numbers to the destination asset
        # Step 1: Snapshot the serials to transfer BEFORE any write
        serials_to_transfer = record.serial_number_ids
        if serials_to_transfer:
            # Step 2: Detach from source asset first (prevents re-link via form save)
            serials_to_transfer.sudo().write({'asset_id': new_asset.id})

            # Step 3: Invalidate cache on source asset so serial_number_ids
            #         reflects the removal immediately in any subsequent reads
            asset.invalidate_recordset(['serial_number_ids'])

        # Mark the transfer entry as linked to the new branch asset and closed
        record.sudo().write({
            'asset_id': new_asset.id,
            'status': 'returned',
        })

    def write(self, vals):
        """On write, trigger branch transfer only when to_branch_id is newly set."""
        # Remember which records already had a to_branch_id before the write
        already_transferred = {
            r.id: (r.to_branch_id and r.asset_id.company_id != r.to_branch_id)
            for r in self
        }
        res = super(AssetTransferEntry, self).write(vals)
        for record in self:
            if (
                record.to_branch_id
                and record.asset_id.company_id != record.to_branch_id
                and not already_transferred.get(record.id)
            ):
                self._do_branch_transfer(record)
        return res

    @api.constrains('status', 'asset_id', 'stock_qty')
    def _check_stock_availability(self):
        """Ensure stock is available when assigning assets (employee assignments only)."""
        for record in self:
            if record.status == 'assigned' and not record.to_branch_id:
                # current_stock is the live on-hand quantity; check against it
                other_assigned = self.search([
                    ('asset_id', '=', record.asset_id.id),
                    ('status', '=', 'assigned'),
                    ('id', '!=', record.id),
                ])
                total_assigned = sum(other_assigned.mapped('stock_qty'))
                available = record.asset_id.current_stock - total_assigned
                if available < record.stock_qty:
                    raise exceptions.ValidationError(_("Cannot assign this asset: Insufficient stock available."))

class AssetMaintenanceEntry(models.Model):
    _name = 'asset.maintenance.entry'
    _description = 'Asset Maintenance Entry'

    # Fields for tracking asset maintenance
    asset_id = fields.Many2one('asset.management', string="Asset Reference", help="Choose the asset for undergoing maintenance or repair is being recorded")
    serial_number_id = fields.Many2one('asset.serial.number', string="Serial Number", help="Select the specific serial number undergoing maintenance")
    maintenance_type = fields.Selection([
        ('preventive', 'Preventive'),
        ('breakdown', 'Breakdown'),
    ], string="Maintenance Type", help="Type of maintenance: Preventive (scheduled) or Breakdown (unplanned)")
    maintenance_vendor_id = fields.Many2one('asset.vendor', string="Select Vendor", help="Vendor or technician performing the maintenance or repair")
    amc_vendor_id = fields.Many2one('asset.vendor', string="AMC Vendor", help="Annual Maintenance Contract vendor responsible for this asset")
    amc_cost = fields.Float(string="AMC Cost", help="Annual Maintenance Contract cost")
    product_id = fields.Many2one('product.product', string="Product / Equipment",
                                 help="Select an existing product from inventory used as maintenance equipment or spare part")
    assign_date = fields.Date(string="Service Start Date", help="Date when the asset was sent for maintenance or repair")
    assign_by = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user, help="Person who initiated the maintenance or repair request")
    return_date = fields.Date(string="Completion Date", help="Date when the maintenance or repair was completed")
    maintenance_status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ], string="Status", help="Current status of the maintenance or repair process")
    maintenance_amount = fields.Float(string="Service Cost", help="Cost of this maintenance service")
    downtime_days = fields.Integer(string="Downtime (Days)", compute='_compute_downtime_days', store=True, help="Number of days the asset was unavailable during maintenance")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    file_name = fields.Char(string='File Name')
    document = fields.Binary(string='Documents', required=True)

    @api.depends('assign_date', 'return_date')
    def _compute_downtime_days(self):
        for record in self:
            if record.assign_date and record.return_date:
                delta = record.return_date - record.assign_date
                record.downtime_days = max(delta.days, 0)
            else:
                record.downtime_days = 0


class AssetDepreciationEntry(models.Model):
    _name = 'asset.depreciation.entry'
    _description = 'Asset Depreciation Entry'

    # Fields for tracking asset depreciation
    asset_id = fields.Many2one('asset.management', string="Asset Reference", help="Choose the asset for which depreciation is being recorded")
    product_id = fields.Many2one('product.product', string="Product", related='asset_id.product_id', store=True, readonly=True)
    bill_id = fields.Many2one('account.move', string="Bill Reference", domain="[('move_type', 'in', ['in_invoice', 'in_refund'])]", help="Vendor bill associated with this depreciation entry")
    depreciation_amount = fields.Float(string="Amount", help="The monetary value of depreciation applied in this entry")
    entry_date = fields.Date(string="Depreciation Date", help="Date when this depreciation entry was recorded")
    state = fields.Selection([('draft', 'Planned'), ('posted', 'Posted')], string='Status', default='posted')
    notes = fields.Text(string="Comments", help="Additional information or remarks about this depreciation entry")
    created_by = fields.Many2one('res.users', string="Recorded By", default=lambda self: self.env.user, help="Person who created this depreciation entry")


class AssetType(models.Model):
    _name = 'asset.type'
    _description = 'Asset Type'

    # Fields for defining asset types and their depreciation rules
    name = fields.Char(string='Name', required=True)
    color = fields.Integer(string='Color Index', help="Color index for this asset type")
    depreciation_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('days', 'Days')
    ], string='Depreciation Frequency', required=True, help="How often depreciation is calculated (Yearly, Monthly, or Daily)")

    depreciation_method = fields.Selection([
        ('fix', 'Fix'),
        ('percentage', 'Percentage')
    ], string='Depreciation Value Type', required=True, help="Whether depreciation is calculated as a percentage or fixed amount")
    color = fields.Integer(string='Color Index', default=0)

    depreciation_rate = fields.Float(string='Depreciation Rate', help="The percentage or fixed amount used to calculate depreciation")
    depreciation_start_delay = fields.Integer(string='Depreciation Start Delay', help="Time duration before depreciation begins after asset acquisition")
    depreciation_basis = fields.Selection([
        ('real_value', 'Purchase Price'),
        ('depreciation_value', 'Book Price')
    ], string='Depreciation Basis', required=True, help="Whether depreciation is applied to the adjusted value (after previous depreciation) or the original value")
    maximum_depreciation_entries = fields.Integer(string="Maximum Depreciation Entries", help="The maximum number of depreciation entries allowed for this asset type")

    asset_count = fields.Integer(compute='_compute_asset_stats')
    total_booked_value = fields.Monetary(compute='_compute_asset_stats', string="Total Booked Value", currency_field='currency_id')
    total_current_value = fields.Monetary(compute='_compute_asset_stats', string="Current Value", currency_field='currency_id')
    total_transfer_count = fields.Integer(compute='_compute_asset_stats', string="Total Transfers")
    total_maintenance_count = fields.Integer(compute='_compute_asset_stats', string="Total Maintenance")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def _compute_asset_stats(self):
        for record in self:
            # Aggregate stats across all companies if in Main Company, or specific companies if in branch
            domain = [('asset_type_id', '=', record.id), ('asset_status', '!=', 'expired')]
            
            # If the active company has a parent, it's a branch: restrict to current active selection.
            # If it has no parent, it's the Main Company: show everything from all branches.
            if self.env.company.parent_id:
                domain.append(('company_id', 'in', self.env.companies.ids))
            
            assets = self.env['asset.management'].search(domain)
            record.asset_count = len(assets)
            record.total_booked_value = sum(assets.mapped('amount'))
            record.total_current_value = sum(assets.mapped('current_amount'))
            record.total_transfer_count = sum(assets.mapped('transfer_count'))
            record.total_maintenance_count = sum(assets.mapped('maintenance_count'))

    def action_open_assets(self):
        self.ensure_one()
        # Create a new dashboard drill-down wizard for the selected type
        wizard = self.env['asset.dashboard.wizard'].create({
            'asset_type_id': self.id
        })
        wizard.populate_summary_lines()
        
        action = self.env.ref('asset_management.action_asset_dashboard_wizard').read()[0]
        action.update({
            'res_id': wizard.id,
            'target': 'new',
            'view_mode': 'form',
        })
        return action