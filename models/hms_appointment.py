from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta  # Ensure this is imported


class HmsAppointment(models.Model):
    _name = 'hms.appointment'
    _description = 'Hospital Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "appointment_date desc, priority desc"

    name = fields.Char(string='Appointment ID', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('hms.appointment'))
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hms.doctor', string='Doctor', required=True, tracking=True)
    appointment_date = fields.Datetime(string='Appointment Date', required=True, default=fields.Datetime.now,
                                       tracking=True)
    appointment_date_day_code = fields.Char(compute='_compute_appointment_date_day_code', store=True, readonly=True)

    duration = fields.Float(string='Duration (Hours)', default=0.5, tracking=True)  # e.g., 0.5 for 30 mins
    end_datetime = fields.Datetime(string='End Date & Time', compute='_compute_end_datetime', store=True, readonly=True)

    reason = fields.Text(string='Reason for Appointment', tracking=True)
    notes = fields.Text(string='Notes')
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Low'),
        ('2', 'High'),
        ('3', 'Very High')
    ], string='Priority', default='0', tracking=True)

    appointment_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('check_up', 'Check-up'),
        ('emergency', 'Emergency')
    ], string='Appointment Type', default='consultation', required=True, tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    medical_record_ids = fields.One2many('hms.medical.record', 'appointment_id', string='Medical Records')
    medical_record_count = fields.Integer(compute='_compute_medical_record_count', string="Medical Records Count")

    # Billing
    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False, readonly=True)
    invoice_status = fields.Selection(related='invoice_id.payment_state', string="Invoice Status", readonly=True,
                                      store=True)

    @api.depends('appointment_date')
    def _compute_appointment_date_day_code(self):
        for record in self:
            if record.appointment_date:
                record.appointment_date_day_code = record.appointment_date.strftime('%A').lower()
            else:
                record.appointment_date_day_code = False

    @api.depends('appointment_date', 'duration')
    def _compute_end_datetime(self):
        for record in self:
            if record.appointment_date and record.duration > 0:
                record.end_datetime = record.appointment_date + timedelta(hours=record.duration)
            else:
                record.end_datetime = record.appointment_date  # Or False if duration is mandatory

    @api.depends('medical_record_ids')
    def _compute_medical_record_count(self):
        for record in self:
            record.medical_record_count = len(record.medical_record_ids)

    @api.constrains('appointment_date', 'doctor_id', 'duration')
    def _check_doctor_availability_and_overlapping_appointments(self):
        for record in self:
            if not record.appointment_date or not record.doctor_id or not record.duration > 0:
                continue  # Validation handled by required fields or other constraints

            # Check doctor's available days
            appointment_day_code = record.appointment_date.strftime('%A').lower()
            if appointment_day_code not in record.doctor_id.available_days.mapped('code'):
                available_days_str = ", ".join(d.name for d in record.doctor_id.available_days)
                raise ValidationError(
                    _("Doctor %s is not available on %s. Available days: %s.") %
                    (record.doctor_id.name, record.appointment_date.strftime('%A'),
                     available_days_str or _("None specified"))
                )

            # Check for overlapping appointments for the same doctor
            start_time = record.appointment_date
            end_time = record.end_datetime

            overlapping_appointments = self.search([
                ('id', '!=', record.id),
                ('doctor_id', '=', record.doctor_id.id),
                ('state', 'not in', ['cancelled']),
                # Overlap condition:
                # (ExistingStart < NewEnd) and (ExistingEnd > NewStart)
                ('appointment_date', '<', end_time),
                ('end_datetime', '>', start_time),
            ])
            if overlapping_appointments:
                raise ValidationError(
                    _("Doctor %s already has an overlapping appointment at this time: %s.") %
                    (record.doctor_id.name, ", ".join(overlapping_appointments.mapped('name')))
                )

    def _get_consultation_product(self):
        product = self.env['product.product'].search([('default_code', '=', 'CONSULT_FEE_HMS')], limit=1)
        if not product:
            raise UserError(
                _("The 'Consultation Fee' product (default_code='CONSULT_FEE_HMS') is not defined. Please create it first."))
        if product.type != 'service':
            raise UserError(_("The 'Consultation Fee' product must be of type 'Service'."))
        return product

    def _prepare_invoice_values(self, consultation_product, existing_invoice=None):
        self.ensure_one()
        if not self.patient_id.partner_id:
            raise UserError(
                _("Patient %s does not have a linked partner record. Cannot create/update invoice.") % self.patient_id.name)

        invoice_lines_to_add = []
        if self.doctor_id and self.doctor_id.consultation_fee > 0:
            line_name = _("Consultation with %s") % self.doctor_id.display_name
            already_exists = False
            if existing_invoice:
                for line in existing_invoice.invoice_line_ids:
                    if line.product_id == consultation_product and line.name == line_name and line.price_unit == self.doctor_id.consultation_fee:
                        already_exists = True
                        break
            if not already_exists:
                invoice_lines_to_add.append((0, 0, {
                    'product_id': consultation_product.id,
                    'name': line_name,
                    'quantity': 1,
                    'price_unit': self.doctor_id.consultation_fee,
                }))

        if not invoice_lines_to_add and not existing_invoice:
            return False

        if existing_invoice:
            if invoice_lines_to_add:
                existing_invoice.write({'invoice_line_ids': invoice_lines_to_add})
            return existing_invoice
        else:
            return {
                'move_type': 'out_invoice',
                'partner_id': self.patient_id.partner_id.id,
                'invoice_date': fields.Date.context_today(self),
                'invoice_origin': self.name,
                'narration': _("Invoice for appointment %s.") % self.name,
                'invoice_line_ids': invoice_lines_to_add,
                'company_id': self.env.company.id,
            }

    def action_create_invoice(self):
        invoice_created_or_updated = False
        for record in self:
            if record.state != 'completed':
                raise UserError(_("Cannot create invoice for appointment %s as it is not completed.") % record.name)
            if not record.patient_id.partner_id:
                raise UserError(
                    _("Patient %s for appointment %s does not have a linked partner.") % (record.patient_id.name,
                                                                                          record.name))

            consultation_product = record._get_consultation_product()

            if record.invoice_id and record.invoice_id.state == 'draft':
                invoice_obj = record._prepare_invoice_values(consultation_product, existing_invoice=record.invoice_id)
                if invoice_obj:
                    record.message_post(body=_(
                        "Consultation fee added to existing draft Invoice <a href='#' data-oe-model='account.move' data-oe-id='%d'>%s</a>.") % (
                                                 record.invoice_id.id, record.invoice_id.name))
                    invoice_created_or_updated = True
            elif not record.invoice_id:
                invoice_vals = record._prepare_invoice_values(consultation_product)
                if not invoice_vals or not invoice_vals.get('invoice_line_ids'):
                    record.message_post(body=_(
                        "No invoice created for appointment %s as there were no new billable items (e.g., consultation fee is zero or already invoiced).") % record.name)
                    continue
                invoice = self.env['account.move'].create(invoice_vals)
                record.invoice_id = invoice.id
                record.message_post(
                    body=_(
                        "Invoice <a href='#' data-oe-model='account.move' data-oe-id='%d'>%s</a> created for appointment %s.") % (
                             invoice.id, invoice.name, record.name),
                    subject=_("Invoice Created for Appointment %s") % record.name
                )
                invoice_created_or_updated = True
            elif record.invoice_id and record.invoice_id.state != 'draft':
                record.message_post(body=_(
                    "Consultation fee not added. Invoice <a href='#' data-oe-model='account.move' data-oe-id='%d'>%s</a> is not in draft state.") % (
                                             record.invoice_id.id, record.invoice_id.name))
        return invoice_created_or_updated

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft appointments can be confirmed."))
            record.state = 'confirmed'
            record.message_post(body=_("Appointment <b>%s</b> confirmed.") % record.display_name)
        return True

    def action_start(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Only confirmed appointments can be started."))
            record.state = 'in_progress'
            record.message_post(body=_("Appointment <b>%s</b> is now in progress.") % record.display_name)
        return True

    def action_complete(self):
        res = True
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_("Only in-progress appointments can be completed."))

            record.state = 'completed'
            record.message_post(
                body=_("Appointment <b>%s</b> has been marked as completed.") % record.display_name,
                subject=_("Appointment Completed: %s") % record.name
            )

            # Create medical record if not already linked to one from this appointment
            if not record.medical_record_ids.filtered(lambda mr: mr.appointment_id == record):
                medical_record_vals = {
                    'patient_id': record.patient_id.id,
                    'doctor_id': record.doctor_id.id,
                    'appointment_id': record.id,
                    'date': record.appointment_date,  # Or fields.Datetime.now() if preferred
                    'chief_complaint': record.reason or _('Follow-up/Consultation from appointment %s') % record.name,
                }
                medical_record = self.env['hms.medical.record'].create(medical_record_vals)
                record.message_post(
                    body=_(
                        "A new medical record <a href='#' data-oe-model='hms.medical.record' data-oe-id='%d'>%s</a> has been created for this appointment.") % (
                             medical_record.id, medical_record.name),
                    subject=_("Medical Record Created for Appointment %s") % record.name
                )

            # Attempt to create/update invoice
            if record.doctor_id and record.doctor_id.consultation_fee > 0 or (
                    record.invoice_id and record.invoice_id.state == 'draft'):
                try:
                    record.action_create_invoice()
                except UserError as e:
                    record.message_post(body=_("Appointment completed. Invoice processing issue: %s") % str(e))
                except Exception as e:  # Catch any other unexpected error
                    self.env.cr.rollback()  # Rollback transaction to avoid partial data
                    raise UserError(
                        _("An unexpected error occurred during invoice creation for appointment %s: %s. Please try again or contact support.") % (
                            record.name, str(e)))
            else:
                record.message_post(body=_(
                    "Appointment completed. No invoice action taken as consultation fee is zero or no existing draft invoice to update."))
        return res

    def action_cancel(self):
        for record in self:
            if record.state in ('completed', 'cancelled'):
                raise UserError(_("Cannot cancel an appointment that is already %s.") % record.state)
            if record.invoice_id and record.invoice_id.state not in ('draft', 'cancel'):
                raise UserError(
                    _("Cannot cancel appointment %s as it has a processed invoice (%s). Please cancel the invoice first.") % (
                        record.name, record.invoice_id.name))

            # Cancel related draft invoice
            if record.invoice_id and record.invoice_id.state == 'draft':
                record.invoice_id.button_cancel()  # Or button_draft then button_cancel if needed
                record.message_post(body=_(
                    "Draft invoice %s associated with the appointment has been cancelled.") % record.invoice_id.name)

            previous_state_display = dict(self._fields['state'].selection).get(record.state, record.state)
            record.state = 'cancelled'
            record.message_post(
                body=_("Appointment <b>%s</b> (was %s) has been cancelled.") % (record.display_name,
                                                                                previous_state_display),
                subject=_("Appointment Cancelled: %s") % record.name
            )
        return True

    def action_view_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_("No invoice found for this appointment."))
        return {
            'name': _('Invoice'),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'type': 'ir.actions.act_window',
            'context': {'create': False}
        }

    def action_view_medical_records(self):
        self.ensure_one()
        return {
            'name': _('Medical Records'),
            'type': 'ir.actions.act_window',
            'res_model': 'hms.medical.record',
            'view_mode': 'tree,form',
            'domain': [('appointment_id', '=', self.id)],
            'context': {
                'default_patient_id': self.patient_id.id,
                'default_doctor_id': self.doctor_id.id,
                'default_appointment_id': self.id,
            }
        }

    def _expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]