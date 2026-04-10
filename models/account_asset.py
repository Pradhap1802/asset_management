from odoo import models, fields, api


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
        Sync posted depreciation moves from account.asset to asset.depreciation.entry.
        Only adds NEW entries not already recorded.
        """
        self.ensure_one()
        posted_moves = self.depreciation_move_ids.filtered(
            lambda m: m.state == 'posted' and m.depreciation_value
        ).sorted(key=lambda m: m.date)

        # Get already synced entry dates to avoid duplicates
        existing_dates = set(mgmt_record.depreciation_ids.mapped('entry_date'))

        for move in posted_moves:
            if move.date not in existing_dates:
                self.env['asset.depreciation.entry'].create({
                    'asset_id': mgmt_record.id,
                    'depreciation_amount': abs(move.depreciation_value),
                    'entry_date': move.date,
                    'notes': 'Auto-synced from Accounting: %s' % self.name,
                    'created_by': self.env.uid,
                })

    # -------------------------------------------------------------------------
    # MAIN SYNC METHOD
    # -------------------------------------------------------------------------
    def _sync_to_asset_management(self):
        """
        Create or update the corresponding asset.management record
        with all essential details from the Enterprise accounting asset.
        """
        for asset in self:
            if asset.state == 'model':
                continue

            invoice = asset._get_invoice_from_move_lines()
            vendor_partner = asset._get_vendor_from_invoice()
            product = asset._get_product_from_invoice()
            asset_type = asset._get_or_create_asset_type()

            vals = {
                'name': asset.name,
                'amount': asset.original_value or 0.0,
                'invoice_date': asset.acquisition_date or fields.Date.today(),
                'invoice_id': invoice.id if invoice else False,
                'vendor_partner_id': vendor_partner.id if vendor_partner else False,
                'product_id': product.id if product else False,
                'asset_type_id': asset_type.id if asset_type else False,
                'depreciation_apply': bool(asset_type),
            }

            if asset.asset_management_id:
                # Update existing record
                asset.asset_management_id.write(vals)
                mgmt_record = asset.asset_management_id
            else:
                # Create new record in asset.management and link back
                mgmt_record = self.env['asset.management'].create({
                    **vals,
                    'accounting_asset_id': asset.id,
                })
                asset.asset_management_id = mgmt_record.id

            # Sync any posted depreciation entries
            asset._sync_depreciation_entries(mgmt_record)

    # -------------------------------------------------------------------------
    # ORM OVERRIDES
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super(AccountAsset, self).create(vals_list)
        records._sync_to_asset_management()
        return records

    def write(self, vals):
        result = super(AccountAsset, self).write(vals)
        sync_triggers = {
            'name', 'original_value', 'acquisition_date',
            'original_move_line_ids', 'state', 'model_id',
            'method', 'method_period', 'method_number', 'method_progress_factor',
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
