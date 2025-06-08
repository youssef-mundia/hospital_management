from odoo import models, fields, api


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
    appointment_id = fields.Many2one('hms.appointment', string='Appointment')
    
    # Record Details
    date = fields.Datetime(string='Record Date', default=fields.Datetime.now, required=True)
    chief_complaint = fields.Text(string='Chief Complaint')
    symptoms = fields.Text(string='Symptoms')
    diagnosis = fields.Text(string='Diagnosis')
    treatment = fields.Text(string='Treatment')
    prescription = fields.Text(string='Prescription')
    recommendations = fields.Text(string='Recommendations')
    
    # Vital Signs
    temperature = fields.Float(string='Temperature (°C)')
    blood_pressure_systolic = fields.Integer(string='Blood Pressure (Systolic)')
    blood_pressure_diastolic = fields.Integer(string='Blood Pressure (Diastolic)')
    heart_rate = fields.Integer(string='Heart Rate (BPM)')
    weight = fields.Float(string='Weight (kg)')
    height = fields.Float(string='Height (cm)')
    
    # Follow-up
    follow_up_required = fields.Boolean(string='Follow-up Required')
    follow_up_date = fields.Date(string='Follow-up Date')
    
    @api.depends('name', 'patient_id', 'date')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.name} - {record.patient_id.name} ({record.date.strftime('%Y-%m-%d')})"