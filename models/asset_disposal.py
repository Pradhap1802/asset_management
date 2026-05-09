import logging
from odoo import models, fields, api, _, exceptions

_logger = logging.getLogger(__name__)


class AssetDisposal(models.Model):
    _name = 'asset.disposal'
    _description = 'Asset Disposal'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'disposal_date desc, id desc'

    # -------------------------------------------------------------------------
    # Core fields
    # -------------------------------------------------------------------------
    name = fields.Char(
        string="Disposal Reference",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    asset_id = fields.Many2one(
        'asset.management',
        string="Asset",
        required=True,
        ondelete='cascade',
        tracking=True,
        help="The asset being disposed / scrapped",
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        related='asset_id.product_id',
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string="Branch",
        related='asset_id.company_id',
        store=True,
        readonly=True,
    )
    asset_type_id = fields.Many2one(
        'asset.type',
        string="Asset Type",
        related='asset_id.asset_type_id',
        store=True,
        readonly=True,
    )
    serial_number_ids = fields.Many2many(
        'asset.serial.number',
        'asset_disposal_serial_rel',
        'disposal_id',
        'serial_id',
        string="Serial Numbers",
        help="Select the specific serial numbers being disposed / scrapped",
    )

    # -------------------------------------------------------------------------
    # Disposal details
    # -------------------------------------------------------------------------
    disposal_date = fields.Date(
        string="Disposal Date",
        default=fields.Date.today,
        required=True,
        tracking=True,
        help="Date the asset was disposed / scrapped",
    )
    disposal_method = fields.Selection([
        ('scrap', 'Scrap'),
        ('sold', 'Sold'),
        ('donated', 'Donated'),
        ('written_off', 'Written Off'),
        ('other', 'Other'),
    ], string="Disposal Method", default='scrap', required=True, tracking=True)

    disposal_value = fields.Float(
        string="Disposal / Sale Value",
        help="Amount realised from selling or scrapping the asset (0 for scrap/write-off)",
        tracking=True,
    )
    book_value_at_disposal = fields.Float(
        string="Book Value at Disposal",
        help="Net book value of the asset at the time of disposal",
    )
    loss_on_disposal = fields.Float(
        string="Loss / (Gain) on Disposal",
        compute='_compute_loss_on_disposal',
        store=True,
        help="Positive = loss, Negative = gain",
    )

    disposal_reason = fields.Text(
        string="Reason for Disposal",
        tracking=True,
        help="Explain why the asset is being disposed",
    )
    approved_by = fields.Many2one(
        'res.users',
        string="Approved By",
        default=lambda self: self.env.user,
        tracking=True,
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('done', 'Disposed'),
    ], string="Status", default='draft', tracking=True)

    scrap_ids = fields.One2many(
        'stock.scrap',
        'asset_disposal_id',
        string="Stock Scraps",
        help="Linked inventory scrap records",
    )

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------
    @api.depends('book_value_at_disposal', 'disposal_value')
    def _compute_loss_on_disposal(self):
        for rec in self:
            rec.loss_on_disposal = rec.book_value_at_disposal - rec.disposal_value

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Automatically fetch the current book value when the asset is selected."""
        if self.asset_id:
            self.book_value_at_disposal = self.asset_id.current_amount

    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = (
                    self.env['ir.sequence'].next_by_code('asset.disposal') or 'New'
                )
            # Ensure the book value is captured upon creation if omitted
            if 'book_value_at_disposal' not in vals and vals.get('asset_id'):
                asset = self.env['asset.management'].browse(vals['asset_id'])
                vals['book_value_at_disposal'] = asset.current_amount
        records = super().create(vals_list)
        # Handle rare case where disposal is created directly in 'done' state
        for rec in records:
            if rec.state == 'done':
                rec._apply_disposal_stock_reduction()
        return records

    def write(self, vals):
        # Snapshot records NOT yet in 'done' state before the write
        not_yet_done = self.filtered(lambda r: r.state != 'done')
        result = super().write(vals)
        # If state is now 'done' for a record that wasn't done before → reduce stock
        if vals.get('state') == 'done':
            for rec in not_yet_done:
                if rec.state == 'done':
                    rec._apply_disposal_stock_reduction()
        return result

    # -------------------------------------------------------------------------
    # Stock reduction helper (called from write, action_done, and create)
    # -------------------------------------------------------------------------
    def _apply_disposal_stock_reduction(self):
        """
        Reduce stock when a disposal is marked Done:
          1. Reduce asset.management.current_stock (custom tracking field)
          2. Create & validate stock.scrap records to reduce actual Odoo inventory
          3. Retire (delete) disposed serial numbers
          4. Mark the asset expired if stock reaches zero
        """
        self.ensure_one()
        asset = self.asset_id
        if not asset or not asset.product_id:
            return

        product = asset.product_id
        company = asset.company_id or self.env.company
        disposed_qty = len(self.serial_number_ids) if self.serial_number_ids else 1

        # ── 1. Reduce custom current_stock ───────────────────────────────────
        new_stock = max(asset.current_stock - disposed_qty, 0)
        asset.sudo().write({'current_stock': new_stock})

        # ── 2. Create stock.scrap to reduce actual Odoo inventory ────────────
        # Only create scrap if the product is trackable (Storable or Consumable)
        if product.type in ('consu', 'product'):
            # Find the source stock location for the company/branch
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', 'in', [company.id, False])], limit=1
            )
            source_location = warehouse.lot_stock_id if warehouse else self.env['stock.location'].search(
                [('usage', '=', 'internal'), ('company_id', 'in', [company.id, False])], limit=1
            )
            
            # Global Fallback: If no internal location found for company, find ANY internal location
            if not source_location:
                source_location = self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)

            if source_location:
                uom = product.uom_id

                if self.serial_number_ids:
                    # Scrap one unit per serial number, matched to its lot if available
                    for serial in self.serial_number_ids:
                        # Find the matching stock lot
                        lot = self.env['stock.lot'].search([
                            ('name', '=', serial.name),
                            ('product_id', '=', product.id),
                            ('company_id', 'in', [company.id, False]),
                        ], limit=1)
                        scrap_vals = {
                            'product_id': product.id,
                            'product_uom_id': uom.id,
                            'scrap_qty': 1,
                            'location_id': source_location.id,
                            'company_id': company.id,
                            'origin': self.name,
                            'asset_disposal_id': self.id,
                        }
                        if lot:
                            scrap_vals['lot_id'] = lot.id
                        
                        scrap = self.env['stock.scrap'].sudo().create(scrap_vals)
                        # We let do_scrap() raise errors (like 'Insufficient Qty') 
                        # so the user knows why it failed instead of failing silently.
                        scrap.do_scrap()
                else:
                    # No serial selected — scrap 1 unit generically
                    scrap = self.env['stock.scrap'].sudo().create({
                        'product_id': product.id,
                        'product_uom_id': uom.id,
                        'scrap_qty': 1.0,
                        'location_id': source_location.id,
                        'company_id': company.id,
                        'origin': self.name,
                        'asset_disposal_id': self.id,
                    })
                    scrap.do_scrap()
            else:
                _logger.warning("No source location found for scrap in disposal %s", self.name)

        # ── 3. Retire disposed serial numbers permanently ─────────────────────
        if self.serial_number_ids:
            self.serial_number_ids.sudo().unlink()
            asset.invalidate_recordset(['serial_number_ids'])

        # ── 4. Mark asset expired when stock hits zero ────────────────────────
        if new_stock == 0 and asset.asset_status != 'expired':
            asset.sudo().with_context(_no_disposal_sync=True).write({'asset_status': 'expired'})

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'confirmed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Disposal Submitted'),
                'message': _('The asset disposal request has been created and is waiting for administrator approval.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_approve(self):
        if not self.env.user.has_group('asset_management.assets_admin_group') and not self.env.is_admin():
            raise exceptions.UserError(_("Only administrators can approve asset disposals."))
        for rec in self:
            if rec.state == 'confirmed':
                rec.state = 'approved'
                rec.approved_by = self.env.user.id

    def action_done(self):
        for rec in self:
            if rec.state != 'approved':
                continue
            rec.state = 'done'
            # Stock reduction is handled by write() → _apply_disposal_stock_reduction()

    def action_reset_draft(self):
        for rec in self:
            if rec.state == 'done' and rec.asset_id and rec.asset_id.product_id:
                # Restore current_stock
                disposed_qty = 1  # Serial numbers were deleted, so count = 1
                asset = rec.asset_id
                asset.sudo().write({'current_stock': asset.current_stock + disposed_qty})

                # Reverse the scrap via a return stock move into the warehouse location
                company = asset.company_id or self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', company.id)], limit=1
                )
                if warehouse:
                    # Odoo 19: 'scrap_location' boolean field was removed.
                    # Use the global scrap location via XML ref.
                    scrap_location = self.env.ref(
                        'stock.stock_location_scrapped', raise_if_not_found=False
                    )
                    if not scrap_location:
                        # Fallback: find any virtual location used for scrapping
                        scrap_location = self.env['stock.location'].search(
                            [('usage', '=', 'inventory'), ('company_id', 'in', [company.id, False])],
                            limit=1,
                        )
                    dest_location = warehouse.lot_stock_id
                    if scrap_location and dest_location:
                        self.env['stock.move'].sudo().create({
                            # 'name' field is removed in Odoo 19 stock.move
                            'product_id': asset.product_id.id,
                            'product_uom_qty': disposed_qty,
                            'product_uom': asset.product_id.uom_id.id,
                            'location_id': scrap_location.id,
                            'location_dest_id': dest_location.id,
                            'company_id': company.id,
                            'origin': rec.name,
                            'state': 'draft',
                        })._action_confirm()._action_assign()

                # Restore asset status if it was expired only because of this disposal
                if asset.asset_status == 'expired' and asset.current_stock > 0:
                    asset.sudo().with_context(_no_disposal_sync=True).write({'asset_status': 'active'})

            rec.state = 'draft'
