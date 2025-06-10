from odoo import models, fields, api, _
from datetime import date
from dateutil.relativedelta import relativedelta


class HmsPatient(models.Model):
    _name = 'hms.patient'
    _description = 'Hospital Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    patient_id = fields.Char(string='Patient ID', required=True, copy=False, readonly=True,
                             default=lambda self: self.env['ir.sequence'].next_by_code('hms.patient'))
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)

    date_of_birth = fields.Date(string='Date of Birth', tracking=True)
    age = fields.Integer(string='Age (Years)', compute='_compute_age', store=True, tracking=True)
    age_display = fields.Char(string='Precise Age', compute='_compute_age_display', store=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender', tracking=True)
    image = fields.Image(string='Photo')
    marital_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('widowed', 'Widowed'),
        ('divorced', 'Divorced')
    ], string='Marital Status', tracking=True)
    occupation = fields.Char(string='Occupation', tracking=True)

    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')

    blood_group = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ], string='Blood Group')
    allergies = fields.Text(string='Allergies')
    medical_history = fields.Text(string='Medical History')

    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Relation')

    appointment_ids = fields.One2many('hms.appointment', 'patient_id', string='Appointments')
    medical_record_ids = fields.One2many('hms.medical.record', 'patient_id', string='Medical Records')
    insurance_ids = fields.One2many('hms.patient.insurance', 'patient_id', string='Insurances')

    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='restrict',
                                 help="Partner record for billing and other communications.",
                                 copy=False)

    active = fields.Boolean(string='Active', default=True)

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        for patient in self:
            patient_id_str = patient.patient_id or 'N/A'
            patient.display_name = f"[{patient_id_str}] {patient.name or ''}"

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

    @api.depends('date_of_birth')
    def _compute_age_display(self):
        for patient in self:
            if patient.date_of_birth:
                today = date.today()
                age_delta = relativedelta(today, patient.date_of_birth)
                years = age_delta.years
                months = age_delta.months
                days = age_delta.days
                patient.age_display = f"{years} years, {months} months, {days} days"
            else:
                patient.age_display = False

    @api.model_create_multi
    def create(self, vals_list):
        patients = super().create(vals_list)
        for patient in patients:
            if not patient.partner_id:
                partner_vals = patient._prepare_partner_values()
                partner = self.env['res.partner'].create(partner_vals)
                patient.partner_id = partner.id
        return patients

    def write(self, vals):
        res = super().write(vals)
        for patient in self:
            if patient.partner_id and any(key in vals for key in
                                          ['name', 'email', 'phone', 'mobile', 'street', 'street2', 'city', 'state_id',
                                           'zip', 'country_id']):
                partner_vals_to_update = patient._prepare_partner_values()
                if 'name' in partner_vals_to_update and patient.partner_id.name != patient.name and patient.partner_id.name != vals.get(
                        'name'):
                    del partner_vals_to_update['name']

                if partner_vals_to_update:
                    patient.partner_id.write(partner_vals_to_update)
        return res

    def _prepare_partner_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'mobile': self.mobile,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'state_id': self.state_id.id if self.state_id else False,
            'zip': self.zip,
            'country_id': self.country_id.id if self.country_id else False,
            'customer_rank': 1,
        }

    def action_open_partner_form(self):
        self.ensure_one()
        if not self.partner_id:
            partner_vals = self._prepare_partner_values()
            partner = self.env['res.partner'].create(partner_vals)
            self.partner_id = partner.id

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'view_mode': 'form',
            'res_id': self.partner_id.id,
            'target': 'current',
        }