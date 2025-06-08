from odoo import models, fields, api
from datetime import date


class HmsPatient(models.Model):
    _name = 'hms.patient'
    _description = 'Hospital Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    patient_id = fields.Char(string='Patient ID', required=True, copy=False, readonly=True, 
                            default=lambda self: self.env['ir.sequence'].next_by_code('hms.patient'))
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Personal Information
    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(string='Age', compute='_compute_age', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', tracking=True)
    
    # Contact Information
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Medical Information
    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], string='Blood Group')
    allergies = fields.Text(string='Allergies')
    medical_history = fields.Text(string='Medical History')
    
    # Emergency Contact
    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relation')
    
    # Relations
    appointment_ids = fields.One2many('hms.appointment', 'patient_id', string='Appointments')
    medical_record_ids = fields.One2many('hms.medical.record', 'patient_id', string='Medical Records')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for patient in self:
            patient.display_name = f"[{patient.patient_id}] {patient.name}"
    
    @api.depends('date_of_birth')
    def _compute_age(self):
        for patient in self:
            if patient.date_of_birth:
                today = date.today()
                patient.age = today.year - patient.date_of_birth.year - (
                    (today.month, today.day) < (patient.date_of_birth.month, patient.date_of_birth.day)
                )
            else:
                patient.age = 0