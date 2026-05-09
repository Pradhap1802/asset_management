from odoo import models, fields, api

VENDOR_TAG_KEYWORDS = ['vendor','supplier', 'asset vendor']


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Link to the auto-created asset.vendor record
    asset_vendor_id = fields.Many2one(
        'asset.vendor',
        string="Asset Vendor Record",
        copy=False,
        readonly=True,
        help="Linked record in Asset Management Vendors when this contact is tagged as Vendor",
    )

    def _is_asset_vendor(self):
        """Return True if any contact tag matches vendor-related keywords."""
        self.ensure_one()
        for tag in self.category_id:
            if any(kw in tag.name.lower() for kw in VENDOR_TAG_KEYWORDS):
                return True
        return False

    def _sync_to_asset_vendor(self):
        """Create or update the asset.vendor record from this contact."""
        for partner in self:
            if not partner._is_asset_vendor():
                # If vendor tag removed, skip (don't delete the vendor record)
                continue

            # Build address string
            address_parts = filter(None, [
                partner.street,
                partner.city,
                partner.state_id.name if partner.state_id else '',
                partner.country_id.name if partner.country_id else '',
            ])
            address = ', '.join(address_parts)

            vals = {
                'name': partner.name or '',
                'address': address,
                'contact_phone': partner.phone or '',
                'contact_email': partner.email or '',
                'seller': partner.name or '',
            }

            if partner.asset_vendor_id:
                # Update existing asset.vendor record
                partner.asset_vendor_id.write(vals)
            else:
                # Create new asset.vendor record and link back
                vendor_record = self.env['asset.vendor'].create({
                    **vals,
                    'partner_id': partner.id,
                })
                partner.asset_vendor_id = vendor_record.id

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ResPartner, self).create(vals_list)
        records._sync_to_asset_vendor()
        return records

    def write(self, vals):
        result = super(ResPartner, self).write(vals)
        # Sync when tags, name, address, or contact info changes
        sync_triggers = {
            'category_id', 'name', 'street', 'city',
            'state_id', 'country_id', 'phone', 'mobile', 'email',
        }
        if sync_triggers & set(vals.keys()):
            self._sync_to_asset_vendor()
        return result
