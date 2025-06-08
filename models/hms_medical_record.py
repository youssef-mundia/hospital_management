from odoo import models, fields, api, _ # Ajout de _


class HmsMedicalRecord(models.Model):
    _name = 'hms.medical.record'
    _description = 'Medical Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    name = fields.Char(string='Record Reference', required=True, copy=False, readonly=True,
                      default=lambda self: self.env['ir.sequence'].next_by_code('hms.medical.record'))
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    # Main Information
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, tracking=True)
    doctor_id = fields.Many2one('hms.doctor', string='Doctor', required=True, tracking=True)
    appointment_id = fields.Many2one('hms.appointment', string='Appointment', tracking=True)

    # Record Details
    date = fields.Datetime(string='Record Date', default=fields.Datetime.now, required=True, tracking=True)
    chief_complaint = fields.Text(string='Chief Complaint', tracking=True)
    symptoms = fields.Text(string='Symptoms', tracking=True)
    diagnosis = fields.Text(string='Diagnosis', tracking=True)
    treatment = fields.Text(string='Treatment', tracking=True)
    prescription_notes = fields.Text(string='Prescription Notes', tracking=True) # Renommé de prescription à prescription_notes
    recommendations = fields.Text(string='Recommendations', tracking=True)

    # Vital Signs
    temperature = fields.Float(string='Temperature (°C)', tracking=True)
    blood_pressure_systolic = fields.Integer(string='Blood Pressure (Systolic)', tracking=True)
    blood_pressure_diastolic = fields.Integer(string='Blood Pressure (Diastolic)', tracking=True)
    heart_rate = fields.Integer(string='Heart Rate (BPM)', tracking=True)
    weight = fields.Float(string='Weight (kg)', tracking=True)
    height = fields.Float(string='Height (cm)', tracking=True)

    # Follow-up
    follow_up_required = fields.Boolean(string='Follow-up Required', tracking=True)
    follow_up_date = fields.Date(string='Follow-up Date', tracking=True)

    # Pièces jointes
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments',
                                      help="Joindre des résultats de tests, des radiographies, etc.")

    # Lignes de prescription
    prescription_line_ids = fields.One2many('hms.prescription.line', 'medical_record_id',
                                            string='Prescription Lines')

    @api.depends('name', 'patient_id', 'date')
    def _compute_display_name(self):
        for record in self:
            record_date_str = record.date.strftime('%Y-%m-%d') if record.date else 'N/A'
            patient_name_str = record.patient_id.name if record.patient_id else 'N/A'
            record_name_str = record.name if record.name else 'N/A'
            record.display_name = f"{record_name_str} - {patient_name_str} ({record_date_str})"