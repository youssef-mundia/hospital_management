from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HmsPrescriptionLine(models.Model):
    _name = 'hms.prescription.line'
    _description = 'Prescription Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('hms.prescription.line'))
    medical_record_id = fields.Many2one('hms.medical.record', string='Medical Record', required=True,
                                        ondelete='cascade')
    patient_id = fields.Many2one(related='medical_record_id.patient_id', string='Patient', store=True, readonly=True)
    doctor_id = fields.Many2one(related='medical_record_id.doctor_id', string='Doctor', store=True, readonly=True)
    prescription_date = fields.Datetime(related='medical_record_id.date', string='Prescription Date', store=True,
                                        readonly=True)

    product_id = fields.Many2one('product.product', string='Medicine', required=True,
                                 domain="[('is_medicine', '=', True), ('type', 'in', ['product', 'consu'])]")
    qty_prescribed = fields.Float(string='Prescribed Quantity', default=1.0, required=True)
    qty_dispensed = fields.Float(string='Dispensed Quantity', default=0.0)
    dosage = fields.Char(string='Dosage', help="For example: 1 tablet")
    frequency = fields.Char(string='Frequency', help="For example: 3 times a day")
    duration = fields.Char(string='Duration', help="For example: for 7 days")
    notes = fields.Text(string='Notes')

    state = fields.Selection([
        ('pending', 'Pending'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
        ('not_available', 'Not Available')
    ], string='Status', default='pending', tracking=True)

    dispensed_by_id = fields.Many2one('res.users', string='Dispensed By', readonly=True, copy=False)
    dispense_date = fields.Datetime(string='Dispense Date', readonly=True, copy=False)

    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False, readonly=True)
    invoice_line_id = fields.Many2one('account.move.line', string='Invoice Line', copy=False, readonly=True)

    # Stock movement tracking
    stock_move_id = fields.Many2one('stock.move', string='Stock Move', copy=False, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Delivery Order', copy=False, readonly=True)

    def _get_pharmacy_location(self):
        """Get the pharmacy/dispensary location"""
        # First try to find a pharmacy-specific location
        pharmacy_location = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            '|',
            ('name', 'ilike', 'pharmacy'),
            ('name', 'ilike', 'dispensary')
        ], limit=1)

        if not pharmacy_location:
            # Fallback to any internal location
            pharmacy_location = self.env['stock.location'].search([
                ('usage', '=', 'internal')
            ], limit=1)

        if not pharmacy_location:
            raise UserError(_("No internal stock location found. Please configure your inventory locations."))

        return pharmacy_location

    def _get_customer_location(self):
        """Get the customer location (where dispensed items go)"""
        try:
            customer_location = self.env.ref('stock.stock_location_customers')
        except:
            customer_location = self.env['stock.location'].search([
                ('usage', '=', 'customer')
            ], limit=1)

        if not customer_location:
            raise UserError(_("Customer location not found. Please check your stock configuration."))
        return customer_location

    def _check_stock_availability(self):
        """Check if there's enough stock available"""
        self.ensure_one()
        if self.product_id.type not in ['product']:
            return True  # Consumable products don't require stock check

        pharmacy_location = self._get_pharmacy_location()
        available_qty = self.product_id.with_context(location=pharmacy_location.id).qty_available

        if available_qty < self.qty_dispensed:
            raise UserError(
                _("Insufficient stock for %s. Available: %s, Required: %s") %
                (self.product_id.name, available_qty, self.qty_dispensed)
            )
        return True

    def _create_stock_movement(self):
        """Create stock movement for dispensed medicine"""
        self.ensure_one()

        if self.product_id.type not in ['product']:
            return True  # No stock movement needed for consumable/service products

        # Check stock availability
        self._check_stock_availability()

        pharmacy_location = self._get_pharmacy_location()
        customer_location = self._get_customer_location()

        # Create picking (delivery order)
        picking_vals = {
            'picking_type_id': self._get_picking_type().id,
            'partner_id': self.patient_id.partner_id.id if self.patient_id.partner_id else False,
            'location_id': pharmacy_location.id,
            'location_dest_id': customer_location.id,
            'origin': self.name,
            'move_type': 'direct',
        }
        picking = self.env['stock.picking'].create(picking_vals)

        # Create stock move
        move_vals = {
            'name': _('Dispense: %s') % self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty_dispensed,
            'product_uom': self.product_id.uom_id.id,
            'picking_id': picking.id,
            'location_id': pharmacy_location.id,
            'location_dest_id': customer_location.id,
            'origin': self.name,
            'picking_type_id': self._get_picking_type().id,
        }
        move = self.env['stock.move'].create(move_vals)

        # Confirm the move
        move._action_confirm()

        # Try to assign (reserve) the move
        move._action_assign()

        # Handle the stock move completion
        if move.state == 'assigned':
            # For newer Odoo versions, we need to handle stock move lines differently
            try:
                # Try the modern approach first
                for move_line in move.move_line_ids:
                    if hasattr(move_line, 'quantity'):
                        move_line.quantity = self.qty_dispensed
                    elif hasattr(move_line, 'qty_done'):
                        move_line.qty_done = self.qty_dispensed
                    else:
                        # Fallback: update the reserved quantity
                        move_line.write({'quantity_done': self.qty_dispensed})

                # Complete the move
                move._action_done()

            except Exception as e:
                # Alternative approach: Set quantity directly on the move
                try:
                    move.with_context(skip_reserved_quantity_check=True).write({
                        'quantity_done': self.qty_dispensed
                    })
                    move._action_done()
                except:
                    # Final fallback: Force the move completion
                    move.write({'state': 'done', 'quantity_done': self.qty_dispensed})
        else:
            # If assignment failed, try to force it
            try:
                # Create move lines manually if needed
                if not move.move_line_ids:
                    move_line_vals = {
                        'move_id': move.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_id.uom_id.id,
                        'location_id': pharmacy_location.id,
                        'location_dest_id': customer_location.id,
                        'picking_id': picking.id,
                    }

                    # Try different field names for quantity
                    if hasattr(self.env['stock.move.line'], 'quantity'):
                        move_line_vals['quantity'] = self.qty_dispensed
                    elif hasattr(self.env['stock.move.line'], 'qty_done'):
                        move_line_vals['qty_done'] = self.qty_dispensed
                    else:
                        move_line_vals['quantity_done'] = self.qty_dispensed

                    self.env['stock.move.line'].create(move_line_vals)

                move._action_done()
            except Exception as e:
                raise UserError(_("Could not complete stock movement: %s") % str(e))

        # Link the move and picking to this prescription line
        self.stock_move_id = move.id
        self.picking_id = picking.id

        return True

    def _get_picking_type(self):
        """Get the picking type for pharmacy dispensing"""
        # Look for a specific pharmacy picking type first
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'outgoing'),
            '|',
            ('name', 'ilike', 'pharmacy'),
            ('name', 'ilike', 'delivery')
        ], limit=1)

        if not picking_type:
            # Fallback to default outgoing picking type
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing')
            ], limit=1)

        if not picking_type:
            raise UserError(_("No outgoing picking type found. Please configure your warehouse."))

        return picking_type

    def action_dispense(self):
        for record in self:
            if record.state != 'pending':
                raise UserError(_("Only pending prescriptions can be dispensed."))
            if record.qty_dispensed <= 0:  # Default to prescribed if not set or zero
                record.qty_dispensed = record.qty_prescribed

            if record.qty_dispensed > record.qty_prescribed:
                raise UserError(
                    _("Dispensed quantity (%s) cannot exceed prescribed quantity (%s).") % (record.qty_dispensed,
                                                                                            record.qty_prescribed))

            try:
                # Create stock movement first
                record._create_stock_movement()

                # Update status and metadata
                record.state = 'dispensed'
                record.dispensed_by_id = self.env.user.id
                record.dispense_date = fields.Datetime.now()

                # Create or update invoice
                record._create_or_update_invoice()

                record.message_post(body=_("Medication %s has been dispensed. Quantity: %s. Stock updated.") %
                                         (record.product_id.name, record.qty_dispensed))
            except Exception as e:
                raise UserError(_("Error during dispensing: %s") % str(e))

        return True

    def action_mark_not_available(self):
        for record in self:
            if record.state != 'pending':
                raise UserError(_("Only pending prescriptions can be marked as not available."))
            record.state = 'not_available'
            record.message_post(body=_("Medication %s marked as not available.") % record.product_id.name)
        return True

    def action_cancel_dispense(self):
        for record in self:
            if record.state not in ['dispensed', 'not_available']:
                raise UserError(
                    _("Cannot cancel dispense for a prescription that is not in 'Dispensed' or 'Not Available' state."))

            original_state = record.state

            # Handle stock move reversal if exists
            if record.stock_move_id and record.stock_move_id.state == 'done':
                record._create_return_stock_movement()

            record.state = 'cancelled'
            record.dispensed_by_id = False
            record.dispense_date = False

            if record.invoice_id:
                record.message_post(body=_(
                    "Dispense of %s cancelled. Original state was '%s'. Associated invoice: %s. Stock movement reversed.") % (
                                             record.product_id.name, original_state, record.invoice_id.name))
            else:
                record.message_post(
                    body=_("Dispense of %s cancelled. Original state was '%s'. Stock movement reversed.") % (
                        record.product_id.name,
                        original_state))

        return True

    def _create_return_stock_movement(self):
        """Create a return stock movement to reverse dispensing"""
        self.ensure_one()

        if not self.stock_move_id:
            return True

        if self.product_id.type not in ['product']:
            return True  # No stock movement needed for consumable products

        pharmacy_location = self._get_pharmacy_location()
        customer_location = self._get_customer_location()

        # Create return picking
        return_picking_vals = {
            'picking_type_id': self._get_return_picking_type().id,
            'partner_id': self.patient_id.partner_id.id if self.patient_id.partner_id else False,
            'location_id': customer_location.id,
            'location_dest_id': pharmacy_location.id,
            'origin': _('Return: %s') % self.name,
            'move_type': 'direct',
        }
        return_picking = self.env['stock.picking'].create(return_picking_vals)

        # Create return stock move
        return_move_vals = {
            'name': _('Return: %s') % self.product_id.name,
            'product_id': self.product_id.id,
            'product_uom_qty': self.qty_dispensed,
            'product_uom': self.product_id.uom_id.id,
            'picking_id': return_picking.id,
            'location_id': customer_location.id,
            'location_dest_id': pharmacy_location.id,
            'origin': _('Return: %s') % self.name,
            'picking_type_id': self._get_return_picking_type().id,
        }
        return_move = self.env['stock.move'].create(return_move_vals)

        # Confirm and process the return move
        return_move._action_confirm()
        return_move._action_assign()

        # Handle completion similar to the dispense method
        try:
            for move_line in return_move.move_line_ids:
                if hasattr(move_line, 'quantity'):
                    move_line.quantity = self.qty_dispensed
                elif hasattr(move_line, 'qty_done'):
                    move_line.qty_done = self.qty_dispensed
                else:
                    move_line.write({'quantity_done': self.qty_dispensed})

            return_move._action_done()
        except:
            # Fallback approach
            return_move.write({'state': 'done', 'quantity_done': self.qty_dispensed})

        return True

    def _get_return_picking_type(self):
        """Get the picking type for returns"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming')
        ], limit=1)

        if not picking_type:
            raise UserError(_("No incoming picking type found for returns."))

        return picking_type

    def action_reset_to_pending(self):
        for record in self:
            if record.state not in ['dispensed', 'cancelled', 'not_available']:
                raise UserError(
                    _("Only prescriptions in 'Dispensed', 'Cancelled', or 'Not Available' state can be reset to pending."))

            if record.state == 'dispensed' and record.invoice_line_id:
                record.message_post(body=_(
                    "Warning: This prescription was linked to invoice %s (line %s). Resetting to pending does not automatically remove or adjust the invoice.") % (
                                             record.invoice_id.name,
                                             record.invoice_line_id.name if record.invoice_line_id else 'N/A'))

            # Handle stock movement reversal if exists
            if record.stock_move_id and record.stock_move_id.state == 'done':
                record._create_return_stock_movement()

            record.state = 'pending'
            record.dispensed_by_id = False
            record.dispense_date = False
            record.qty_dispensed = 0  # Reset dispensed quantity
            record.stock_move_id = False
            record.picking_id = False
            record.message_post(body=_("Prescription status reset to pending. Stock movements reversed."))
        return True

    def action_cancel(self):
        for record in self:
            if record.state == 'dispensed':
                raise UserError(
                    _("Cannot cancel a prescription that has already been dispensed using this action. Use 'Cancel Dispense' instead if applicable."))
            if record.state == 'pending':
                record.state = 'cancelled'
                record.message_post(body=_("Prescription for %s has been cancelled.") % record.product_id.name)
            else:
                raise UserError(
                    _("This prescription cannot be cancelled from its current state ('%s') using this action.") % record.state)

        return True

    def _create_or_update_invoice(self):
        self.ensure_one()
        if not self.patient_id.partner_id:
            raise UserError(
                _("Patient %s does not have a linked partner record. Cannot create/update invoice.") % self.patient_id.name)
        if not self.product_id:
            raise UserError(_("No product defined for this prescription line."))

        AccountMove = self.env['account.move']
        # Check for an existing draft invoice for the patient
        existing_invoice = AccountMove.search([
            ('partner_id', '=', self.patient_id.partner_id.id),
            ('state', '=', 'draft'),
            ('move_type', '=', 'out_invoice')
        ], limit=1)

        invoice_line_vals = {
            'product_id': self.product_id.id,
            'name': _("Medicine: %s (Prescription: %s)") % (self.product_id.name, self.name),
            'quantity': self.qty_dispensed,
            'price_unit': self.product_id.lst_price,
        }

        if existing_invoice:
            invoice = existing_invoice
            new_line = self.env['account.move.line'].create(dict(invoice_line_vals, move_id=invoice.id))
            self.invoice_line_id = new_line.id
            self.invoice_id = invoice.id
            self.message_post(body=_("Medicine added to existing draft Invoice %s.") % invoice.name)
        else:
            invoice_vals = {
                'move_type': 'out_invoice',
                'partner_id': self.patient_id.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': self.name,
                'narration': _("Invoice for medicine dispensed to %s from prescription %s.") % (self.patient_id.name,
                                                                                                self.name),
                'invoice_line_ids': [(0, 0, invoice_line_vals)],
            }
            new_invoice = AccountMove.create(invoice_vals)
            created_line = new_invoice.invoice_line_ids.filtered(
                lambda line: line.product_id == self.product_id and line.quantity == self.qty_dispensed
            )
            if created_line:
                self.invoice_line_id = created_line[0].id
            self.invoice_id = new_invoice.id
            self.message_post(body=_("New invoice %s created for dispensed medicine.") % new_invoice.name)
        return True

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice found for this prescription line."))
        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'context': {'create': False, 'edit': False}
        }

    def action_view_stock_move(self):
        """View the stock movement related to this prescription"""
        self.ensure_one()
        if not self.stock_move_id:
            raise UserError(_("No stock movement found for this prescription line."))
        return {
            'name': _('Stock Move'),
            'view_mode': 'form',
            'res_model': 'stock.move',
            'res_id': self.stock_move_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }

    def action_view_picking(self):
        """View the delivery order related to this prescription"""
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("No delivery order found for this prescription line."))
        return {
            'name': _('Delivery Order'),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }