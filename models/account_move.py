from odoo import models, api, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        """
        Extend _post:
        1. Sync depreciation moves to asset.management (Enterprise).
        2. Auto-create asset.management records from vendor bills (Community).
        """
        posted = super()._post(soft=soft)

        # --- Enterprise depreciation sync ---
        if 'asset_id' in self._fields:
            depreciation_moves = posted.filtered(
                lambda m: m.asset_id
                and m.asset_move_type == 'depreciation'
                and m.asset_id.asset_management_id
                and m.depreciation_value
            )
            for move in depreciation_moves:
                move.asset_id._sync_depreciation_entries(move.asset_id.asset_management_id)

        # --- Community: auto-create assets from vendor bills ---
        if 'account.asset' not in self.env.registry:
            vendor_bills = posted.filtered(lambda m: m.move_type == 'in_invoice')
            for bill in vendor_bills:
                bill._create_assets_from_bill()

        return posted

    def _create_assets_from_bill(self):
        """
        For each invoice line whose product has can_be_asset=True,
        find or create an asset.management record.
        Grouping: same product_id + company_id share one asset.management.
        """
        self.ensure_one()
        AssetMgmt = self.env['asset.management']

        asset_lines = self.invoice_line_ids.filtered(
            lambda l: l.product_id
            and l.product_id.product_tmpl_id.can_be_asset
            and l.display_type == 'product'
        )

        for line in asset_lines:
            product = line.product_id
            company_id = self.company_id.id

            # Search for existing asset.management for same product + company
            existing = AssetMgmt.search([
                ('product_id', '=', product.id),
                ('company_id', '=', company_id),
            ], limit=1)

            # Get vendor partner and try to link to asset.vendor
            vendor_partner = self.partner_id
            asset_vendor = False
            if vendor_partner:
                asset_vendor = self.env['asset.vendor'].search(
                    [('partner_id', '=', vendor_partner.id)], limit=1
                )

            # Try to get serial numbers and warranty from linked stock moves
            serial_names = []
            warranty_date = False
            po_line = line.purchase_line_id if 'purchase_line_id' in line._fields and line.purchase_line_id else False
            if po_line and 'purchase_line_id' in self.env['stock.move']._fields:
                stock_moves = self.env['stock.move'].search([
                    ('product_id', '=', product.id),
                    ('purchase_line_id', '=', po_line.id),
                ])
                for sm in stock_moves:
                    if sm.asset_warranty_date and not warranty_date:
                        warranty_date = sm.asset_warranty_date
                    for ml in sm.move_line_ids:
                        if ml.lot_id and ml.lot_id.name not in serial_names:
                            serial_names.append(ml.lot_id.name)

            quantity = int(line.quantity) or 1
            amount = line.price_subtotal

            vals = {
                'product_id': product.id,
                'company_id': company_id,
                'amount': amount,
                'invoice_date': self.invoice_date or self.date or fields.Date.today(),
                'invoice_id': self.id,
                'vendor_partner_id': vendor_partner.id if vendor_partner else False,
                'vendor_id': asset_vendor.id if asset_vendor else False,
                'initial_stock': quantity,
            }

            if warranty_date:
                vals['expired_warranty_date'] = warranty_date

            if existing:
                # Update: accumulate stock and amount
                existing.write({
                    'amount': existing.amount + amount,
                    'initial_stock': existing.initial_stock + quantity,
                    'invoice_id': self.id,
                    'vendor_partner_id': vendor_partner.id if vendor_partner else existing.vendor_partner_id.id,
                    'vendor_id': asset_vendor.id if asset_vendor else existing.vendor_id.id,
                })
                mgmt_record = existing
            else:
                mgmt_record = AssetMgmt.create(vals)

            # Create serial number records
            existing_serials = set(mgmt_record.serial_number_ids.mapped('name'))
            for serial_name in serial_names:
                if serial_name not in existing_serials:
                    self.env['asset.serial.number'].create({
                        'asset_id': mgmt_record.id,
                        'name': serial_name,
                    })

    @api.model_create_multi
    def create(self, vals_list):
        """
        Extend create: when new depreciation moves are created (draft board),
        sync them immediately so the schedule appears in asset.management.
        """
        moves = super().create(vals_list)

        if 'asset_id' in self._fields:
            depreciation_moves = moves.filtered(
                lambda m: m.asset_id
                and m.asset_move_type == 'depreciation'
                and m.asset_id.asset_management_id
                and m.depreciation_value
            )
            for move in depreciation_moves:
                move.asset_id._sync_depreciation_entries(move.asset_id.asset_management_id)

        return moves

