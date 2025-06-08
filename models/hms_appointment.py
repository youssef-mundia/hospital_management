from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta


class HmsAppointment(models.Model):
    _name = 'hms.appointment'
    _description = 'Hospital Appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    name = fields.Char(string='Appointment Reference', required=True, copy=False, readonly=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('hms.appointment'))
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    # Main Information
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hms.doctor', string='Doctor', required=True, tracking=True)

    # Schedule
    appointment_date = fields.Datetime(string='Appointment Date & Time', required=True, tracking=True,
                                       default=fields.Datetime.now)
    duration = fields.Float(string='Duration (Hours)', default=0.5, tracking=True)
    end_datetime = fields.Datetime(string='End Date & Time', compute='_compute_end_datetime', store=True)

    appointment_date_day_code = fields.Char(
        string='Appointment Day Code',
        compute='_compute_appointment_date_day_code',
        store=True,
        help="Technical field for domain filtering, stores the day code e.g., 'monday'."
    )

    # Details
    reason = fields.Text(string='Reason for Visit', tracking=True)
    notes = fields.Text(string='Notes')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, group_expand='_expand_states')

    # Relations
    medical_record_ids = fields.One2many('hms.medical.record', 'appointment_id', string='Medical Records')

    # New Fields
    appointment_type = fields.Selection([
        ('consultation', 'Consultation'),
        ('follow_up', 'Follow-up'),
        ('emergency', 'Emergency'),
        ('check_up', 'Check-up'),
        ('other', 'Other')
    ], string='Appointment Type', default='consultation', tracking=True, required=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Medium'),
        ('2', 'High'),
        ('3', 'Urgent')
    ], string='Priority', default='1', tracking=True, required=True)

    @api.depends('appointment_date')
    def _compute_appointment_date_day_code(self):
        for record in self:
            if record.appointment_date:
                record.appointment_date_day_code = record.appointment_date.strftime('%A').lower()
            else:
                record.appointment_date_day_code = False

    @api.onchange('appointment_date')
    def _onchange_appointment_date_update_day_code(self):
        new_day_code = False
        if self.appointment_date:
            new_day_code = self.appointment_date.strftime('%A').lower()

        self.appointment_date_day_code = new_day_code

        doctor_domain_list = []
        if new_day_code:
            doctor_domain_list = [('available_days.code', '=', new_day_code)]
        else:
            doctor_domain_list = [('id', '=', False)]  # Domain that matches nothing

        if self.doctor_id:
            is_doctor_still_valid = False
            if new_day_code and self.doctor_id.id:
                if new_day_code in self.doctor_id.available_days.mapped('code'):
                    is_doctor_still_valid = True

            if not is_doctor_still_valid:
                self.doctor_id = False  # Clear the doctor if not valid for the new day

        return {'domain': {'doctor_id': doctor_domain_list}}

    @api.depends('name', 'patient_id', 'doctor_id.name')
    def _compute_display_name(self):
        for appointment in self:
            parts = []
            if appointment.name:
                parts.append(appointment.name)
            if appointment.patient_id:
                parts.append(appointment.patient_id.display_name)
            if appointment.doctor_id:
                parts.append(appointment.doctor_id.display_name)
            appointment.display_name = " - ".join(filter(None, parts))

    @api.depends('appointment_date', 'duration')
    def _compute_end_datetime(self):
        for appointment in self:
            if appointment.appointment_date and appointment.duration > 0:
                appointment.end_datetime = appointment.appointment_date + timedelta(hours=appointment.duration)
            else:
                appointment.end_datetime = appointment.appointment_date  # Or False

    # --- Constraints ---
    @api.constrains('appointment_date', 'state')
    def _check_appointment_date_past(self):
        for record in self:
            if record.appointment_date and record.state == 'draft':
                # Using a small buffer to avoid issues with near-now creations
                if record.appointment_date < datetime.now() - timedelta(minutes=1):
                    raise ValidationError(_("The appointment date cannot be in the past for a draft appointment."))

    @api.constrains('duration')
    def _check_duration_positive(self):
        for record in self:
            if record.duration <= 0:
                raise ValidationError(_("The duration of an appointment must be positive."))

    @api.constrains('doctor_id', 'appointment_date', 'end_datetime', 'state')
    def _check_doctor_availability(self):
        for record in self:
            if record.doctor_id and record.appointment_date and record.end_datetime and \
                    record.state not in ('cancelled', 'completed'):
                domain = [
                    ('doctor_id', '=', record.doctor_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancelled', 'completed']),
                    ('appointment_date', '<', record.end_datetime),
                    ('end_datetime', '>', record.appointment_date),
                ]
                overlapping_appointments = self.env['hms.appointment'].search_count(domain)
                if overlapping_appointments > 0:
                    raise ValidationError(
                        _("Dr. %s is already booked for the selected time slot. Found %d overlapping appointment(s).") %
                        (record.doctor_id.name, overlapping_appointments)
                    )

    @api.constrains('patient_id', 'appointment_date', 'end_datetime', 'state')
    def _check_patient_availability(self):
        for record in self:
            if record.patient_id and record.appointment_date and record.end_datetime and \
                    record.state not in ('cancelled', 'completed'):
                domain = [
                    ('patient_id', '=', record.patient_id.id),
                    ('id', '!=', record.id),
                    ('state', 'not in', ['cancelled', 'completed']),
                    ('appointment_date', '<', record.end_datetime),
                    ('end_datetime', '>', record.appointment_date),
                ]
                overlapping_appointments = self.env['hms.appointment'].search_count(domain)
                if overlapping_appointments > 0:
                    raise ValidationError(
                        _("Patient %s already has an overlapping appointment at the selected time. Found %d overlapping appointment(s).") %
                        (record.patient_id.name, overlapping_appointments)
                    )

    # --- Action Methods ---
    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(_("Only draft appointments can be confirmed."))
            record.state = 'confirmed'
            record.message_post(
                body=_("Appointment <b>%s</b> confirmed by %s.") % (record.display_name, self.env.user.name),
                subject=_("Appointment Confirmed: %s") % record.name
            )
        return True

    def action_start(self):
        for record in self:
            if record.state != 'confirmed':
                raise UserError(_("Only confirmed appointments can be started."))
            record.state = 'in_progress'
            record.message_post(body=_("Appointment <b>%s</b> is now in progress.") % record.display_name)
        return True

    def action_complete(self):
        for record in self:
            if record.state != 'in_progress':
                raise UserError(_("Only appointments in progress can be completed."))
            record.state = 'completed'
            record.message_post(body=_("Appointment <b>%s</b> has been completed.") % record.display_name)

            if not record.medical_record_ids:
                medical_record_vals = {
                    'patient_id': record.patient_id.id,
                    'doctor_id': record.doctor_id.id,
                    'appointment_id': record.id,
                    'date': record.appointment_date,
                    'chief_complaint': record.reason or _('Follow-up/Consultation from appointment %s') % record.name,
                }
                medical_record = self.env['hms.medical.record'].create(medical_record_vals)
                record.message_post(
                    body=_(
                        "A new medical record <a href='#' data-oe-model='hms.medical.record' data-oe-id='%d'>%s</a> has been created for this appointment.") % (
                             medical_record.id, medical_record.name),
                    subject=_("Medical Record Created for Appointment %s") % record.name
                )
            else:
                record.message_post(
                    body=_("This appointment is already linked to medical record(s): %s") % (
                        ", ".join(mr.name for mr in record.medical_record_ids))
                )
        return True

    def action_cancel(self):
        for record in self:
            if record.state in ('completed', 'cancelled'):
                raise UserError(_("Cannot cancel an appointment that is already %s.") % record.state)
            previous_state_display = dict(self._fields['state'].selection).get(record.state, record.state)
            record.state = 'cancelled'
            record.message_post(
                body=_("Appointment <b>%s</b> (was %s) has been cancelled.") % (record.display_name,
                                                                                previous_state_display),
                subject=_("Appointment Cancelled: %s") % record.name
            )
        return True

    def _expand_states(self, states, domain, order):
        return [key for key, val in self._fields['state'].selection]