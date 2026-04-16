from odoo import models, fields, api
from odoo.orm.models import MetaModel
from datetime import timedelta

# Only define these classes if account_asset enterprise module is actually loaded.
# get_module_path finds the directory on disk even when not installed, so we check
# whether account_asset has registered any model classes via the metaclass.
if not MetaModel._module_to_models__.get('account_asset'):
    # account_asset not installed — skip all class definitions
    raise ImportError("account_asset module is not installed")
else:

    class AssetManagementAccountAssetLink(models.Model):
        """Add accounting_asset_id field to asset.management when account_asset is available."""
        _inherit = 'asset.management'

        accounting_asset_id = fields.Many2one(
            'account.asset',
            string="Accounting Asset",
            readonly=True,
            copy=False,
            help="Linked Odoo Enterprise Accounting Asset record",
        )


    class AccountAsset(models.Model):
        _inherit = 'account.asset'

    # Reverse link to the custom asset management record
    asset_management_id = fields.Many2one(
        'asset.management',
        string="Asset Management Record",
        copy=False,
        readonly=True,
        help="Linked physical asset tracking record in Asset Management module",
    )

    # Asset identification and warranty fields
    asset_serial_number = fields.Char(
        string="Serial Number",
        help="Serial number or unique identifier for the asset",
    )

    asset_warranty_date = fields.Date(
        string="Warranty Expiry Date",
        help="Warranty expiry date for the asset",
    )

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------
    def _get_vendor_from_invoice(self):
        """Extract vendor partner from the linked invoice move lines."""
        self.ensure_one()
        if self.original_move_line_ids:
            return self.original_move_line_ids[0].move_id.partner_id
        return self.env['res.partner']

    def _get_invoice_from_move_lines(self):
        """Get the account.move (invoice) linked to this asset."""
        self.ensure_one()
        if self.original_move_line_ids:
            return self.original_move_line_ids[0].move_id
        return self.env['account.move']

    def _get_product_from_invoice(self):
        """Extract the product from the first linked invoice line."""
        self.ensure_one()
        if self.original_move_line_ids:
            return self.original_move_line_ids[0].product_id
        return self.env['product.product']

    def _get_po_line_from_invoice(self):
        """Extract Purchase Order line from the linked invoice move lines."""
        self.ensure_one()
        for line in self.original_move_line_ids:
            if line.purchase_line_id:
                return line.purchase_line_id
        return self.env['purchase.order.line']

    def _get_stock_move_from_invoice(self):
        """Extract stock move related to this asset from invoice via PO line or date fallback."""
        self.ensure_one()
        if not self.original_move_line_ids:
            return self.env['stock.move']

        product = self._get_product_from_invoice()
        if not product:
            return self.env['stock.move']

        # 1. Try via purchase order line link (most reliable)
        po_line = self._get_po_line_from_invoice()
        if po_line:
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('purchase_line_id', '=', po_line.id),
            ], limit=1)
            if stock_moves:
                return stock_moves

        # 2. Fallback: search by product and invoice date range
        invoice = self.original_move_line_ids[0].move_id
        if invoice.invoice_date:
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('create_date', '>=', invoice.invoice_date - timedelta(days=30)),
                ('create_date', '<=', invoice.invoice_date + timedelta(days=30)),
            ], limit=1)
            if stock_moves:
                return stock_moves

        return self.env['stock.move']

    def _get_asset_serial_number(self):
        """Extract serial number from stock move or lot."""
        self.ensure_one()
        stock_move = self._get_stock_move_from_invoice()
        if stock_move:
            if stock_move.move_line_ids and stock_move.move_line_ids[0].lot_id:
                return stock_move.move_line_ids[0].lot_id.name
        return None

    def _get_all_serial_numbers(self):
        """Extract all serial/lot numbers from stock moves linked to this asset's invoice."""
        self.ensure_one()
        serials = []
        product = self._get_product_from_invoice()
        if not product:
            return serials

        # 1. Try via purchase order line (gets all move lines from the receipt)
        po_line = self._get_po_line_from_invoice()
        if po_line:
            stock_moves = self.env['stock.move'].search([
                ('product_id', '=', product.id),
                ('purchase_line_id', '=', po_line.id),
            ])
            for move in stock_moves:
                for ml in move.move_line_ids:
                    if ml.lot_id and ml.lot_id.name not in serials:
                        serials.append(ml.lot_id.name)
            if serials:
                return serials

        # 2. Fallback: from single stock move
        stock_move = self._get_stock_move_from_invoice()
        if stock_move:
            for ml in stock_move.move_line_ids:
                if ml.lot_id and ml.lot_id.name not in serials:
                    serials.append(ml.lot_id.name)
        return serials

    def _get_asset_warranty_date(self):
        """Extract warranty date from stock move."""
        self.ensure_one()
        stock_move = self._get_stock_move_from_invoice()
        if stock_move and stock_move.asset_warranty_date:
            return stock_move.asset_warranty_date
        return None

    def _get_or_create_asset_type(self):
        """
        Find an asset.type matching the Enterprise model_id name.
        If not found, auto-create one based on the asset's depreciation settings.
        """
        self.ensure_one()
        if not self.model_id:
            return self.env['asset.type']

        model_name = self.model_id.name
        # Try to find existing asset.type with same name (case-insensitive)
        asset_type = self.env['asset.type'].search(
            [('name', 'ilike', model_name)], limit=1
        )
        if asset_type:
            return asset_type

        # Map Enterprise method → custom depreciation_method
        method_map = {
            'linear': 'fix',
            'degressive': 'percentage',
            'degressive_then_linear': 'percentage',
        }
        depr_method = method_map.get(self.method, 'fix')

        # Map method_period → depreciation_frequency
        freq_map = {'1': 'monthly', '12': 'yearly'}
        frequency = freq_map.get(str(self.method_period), 'monthly')

        # Rate: for percentage use progress_factor * 100, for fix use calculated amount
        if depr_method == 'percentage':
            rate = self.method_progress_factor * 100
        else:
            # Linear: rate = original_value / method_number (amount per period)
            rate = (self.original_value / self.method_number) if self.method_number else 0.0

        # Create a matching asset.type
        asset_type = self.env['asset.type'].create({
            'name': model_name,
            'depreciation_frequency': frequency,
            'depreciation_method': depr_method,
            'depreciation_rate': rate,
            'depreciation_start_delay': 1,
            'depreciation_basis': 'real_value',
            'maximum_depreciation_entries': self.method_number or 0,
        })
        return asset_type

    # -------------------------------------------------------------------------
    # DEPRECIATION SYNC
    # -------------------------------------------------------------------------
    def _sync_depreciation_entries(self, mgmt_record):
        """
        Sync ALL depreciation moves (both draft and posted) from account.asset
        to asset.depreciation.entry so the full schedule is visible.
        Existing synced entries are rebuilt from the accounting board each time.
        """
        self.ensure_one()
        all_moves = self.depreciation_move_ids.filtered(
            lambda m: m.state in ('draft', 'posted') and m.depreciation_value
        ).sorted(key=lambda m: m.date)

        if not all_moves:
            return

        # Get original bill reference from account.asset
        original_bill = self.original_move_line_ids.move_id[:1]

        # Get existing auto-synced entries (identified by notes prefix)
        existing_synced = mgmt_record.depreciation_ids.filtered(
            lambda e: e.notes and e.notes.startswith('Auto-synced')
        )
        existing_dates = {e.entry_date: e for e in existing_synced}

        for move in all_moves:
            entry_date = move.date
            amount = abs(float(move.depreciation_value))
            status_note = 'Posted' if move.state == 'posted' else 'Planned'
            note = 'Auto-synced [%s] from Accounting: %s' % (status_note, self.name)

            if entry_date in existing_dates:
                # Update existing entry if amount changed or state changed
                existing_entry = existing_dates[entry_date]
                vals = {}
                if existing_entry.depreciation_amount != amount or existing_entry.state != move.state:
                    vals.update({'depreciation_amount': amount, 'notes': note, 'state': move.state})
                if not existing_entry.bill_id and original_bill:
                    vals['bill_id'] = original_bill.id
                if vals:
                    existing_entry.write(vals)
            else:
                # Create new entry
                self.env['asset.depreciation.entry'].create({
                    'asset_id': mgmt_record.id,
                    'depreciation_amount': amount,
                    'entry_date': entry_date,
                    'notes': note,
                    'state': move.state,
                    'bill_id': original_bill.id if original_bill else False,
                    'created_by': self.create_uid.id if self.create_uid else self.env.uid,
                })

        # Recompute sequence and cumulative values on all entries
        all_entries = mgmt_record.depreciation_ids.sorted('entry_date')
        cumulative = 0.0
        for idx, entry in enumerate(all_entries, 1):
            cumulative += entry.depreciation_amount
            entry.write({
                'sequence': idx,
                'cumulative_depreciation': cumulative,
                'remaining_value': mgmt_record.amount - cumulative,
            })

    # -------------------------------------------------------------------------
    # MAIN SYNC METHOD
    # -------------------------------------------------------------------------
    def _sync_to_asset_management(self):
        """
        Create or update the corresponding asset.management record.
        GROUPING RULE: All account.asset records with the SAME product_id
        and company_id share ONE asset.management record.
        The initial_stock represents the total counts of this asset.
        """
        for asset in self:
            if asset.state == 'model':
                continue

            invoice = asset._get_invoice_from_move_lines()
            target_company_id = invoice.company_id.id if invoice and invoice.company_id else (asset.company_id.id if asset.company_id else False)
            vendor_partner = asset._get_vendor_from_invoice()
            product = asset._get_product_from_invoice()
            
            po_line = asset._get_po_line_from_invoice()
            
            asset_type = asset._get_or_create_asset_type()

            # Find existing management record for this product and company
            existing_mgmt = None
            if product:
                domain = [
                    ('product_id', '=', product.id),
                    ('company_id', '=', target_company_id),
                ]
                
                existing_mgmt = self.env['asset.management'].search(domain, limit=1)

            if not existing_mgmt and asset.asset_management_id:
                existing_mgmt = asset.asset_management_id

            if existing_mgmt:
                # Get siblings already pointing to this management record
                sibling_assets = self.env['account.asset'].search([('asset_management_id', '=', existing_mgmt.id)])
                if asset.id not in sibling_assets.ids:
                    sibling_assets |= asset
            else:
                sibling_assets = asset
            
            total_count = len(sibling_assets)

            vals = {
                'amount': sum(sibling_assets.mapped('original_value')),  # Summing total value of all assets!
                'invoice_date': asset.acquisition_date or fields.Date.today(),
                'invoice_id': invoice.id if invoice else False,
                'vendor_partner_id': vendor_partner.id if vendor_partner else False,
                'product_id': product.id if product else False,
                'asset_type_id': asset_type.id if asset_type else False,
                'depreciation_apply': bool(asset_type),
                'initial_stock': total_count,
                'company_id': target_company_id,
            }

            # Get and add serial number: prefer account.asset field, fallback to stock move
            serial_value = asset.asset_serial_number or asset._get_asset_serial_number()
            if serial_value:
                vals['barcode'] = serial_value
            
            # Get and add warranty date: prefer account.asset field, fallback to stock move
            if asset.asset_warranty_date:
                vals['expired_warranty_date'] = asset.asset_warranty_date
            else:
                warranty_date = asset._get_asset_warranty_date()
                if warranty_date:
                    vals['expired_warranty_date'] = warranty_date

            if existing_mgmt:
                # Update the shared record with latest count and cumulative info
                existing_mgmt.write(vals)
                # Ensure all siblings point to this mgmt record
                for sibling in sibling_assets:
                    if sibling.asset_management_id != existing_mgmt:
                        sibling.asset_management_id = existing_mgmt.id
                mgmt_record = existing_mgmt
            else:
                # No existing record — create one shared record
                mgmt_record = self.env['asset.management'].create({
                    **vals,
                    'accounting_asset_id': asset.id,
                })
                # Link all siblings to this newly created record
                for sibling in sibling_assets:
                    sibling.asset_management_id = mgmt_record.id

            # Sync depreciation entries (Note: Depreciation syncing handles accumulating values perfectly)
            asset._sync_depreciation_entries(mgmt_record)

            # Sync serial numbers from all siblings' stock moves
            all_serials = set()
            for sibling in sibling_assets:
                # From account.asset field
                if sibling.asset_serial_number:
                    all_serials.add(sibling.asset_serial_number)
                # From stock move lots
                all_serials.update(sibling._get_all_serial_numbers())

            existing_serials = set(mgmt_record.serial_number_ids.mapped('name'))
            for serial_name in all_serials - existing_serials:
                self.env['asset.serial.number'].create({
                    'asset_id': mgmt_record.id,
                    'name': serial_name,
                })


    # -------------------------------------------------------------------------
    # ORM OVERRIDES
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Auto-populate serial number and warranty date from stock move before creating
        for vals in vals_list:
            # Create temporary record to use helper methods
            temp_record = self.new(vals)
            
            # Get serial number from stock move if not already provided
            if not vals.get('asset_serial_number'):
                serial_number = temp_record._get_asset_serial_number()
                if serial_number:
                    vals['asset_serial_number'] = serial_number
            
            # Get warranty date from stock move if not already provided
            if not vals.get('asset_warranty_date'):
                warranty_date = temp_record._get_asset_warranty_date()
                if warranty_date:
                    vals['asset_warranty_date'] = warranty_date
        
        records = super(AccountAsset, self).create(vals_list)
        records._sync_to_asset_management()
        return records

    def write(self, vals):
        result = super(AccountAsset, self).write(vals)
        sync_triggers = {
            'name', 'original_value', 'acquisition_date',
            'original_move_line_ids', 'state', 'model_id',
            'method', 'method_period', 'method_number', 'method_progress_factor',
            'company_id', 'asset_serial_number', 'asset_warranty_date',
        }
        if sync_triggers & set(vals.keys()):
            self._sync_to_asset_management()
        return result

    def compute_depreciation_board(self, date=False):
        """Override to also sync depreciation entries after board is computed."""
        result = super().compute_depreciation_board(date=date)
        for asset in self:
            if asset.asset_management_id:
                asset._sync_depreciation_entries(asset.asset_management_id)
        return result
