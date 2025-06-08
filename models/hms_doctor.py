from odoo import models, fields, api


class HmsDoctor(models.Model):
    _name = 'hms.doctor'
    _description = 'Hospital Doctor'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    name = fields.Char(string='Full Name', required=True, tracking=True)
    doctor_id = fields.Char(string='Doctor ID', required=True, copy=False, readonly=True,
                           default=lambda self: self.env['ir.sequence'].next_by_code('hms.doctor'))
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True)
    
    # Professional Information
    specialization = fields.Char(string='Specialization', required=True, tracking=True)
    license_number = fields.Char(string='License Number', tracking=True)
    qualification = fields.Text(string='Qualification')
    experience_years = fields.Integer(string='Years of Experience')
    
    # Contact Information
    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)
    email = fields.Char(string='Email', tracking=True)
    
    # Department
    department_id = fields.Many2one('hms.department', string='Department', tracking=True)
    
    # Schedule
    consultation_fee = fields.Float(string='Consultation Fee')
    available_days = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday')
    ], string='Available Days', multiple=True)
    
    # Relations
    appointment_ids = fields.One2many('hms.appointment', 'doctor_id', string='Appointments')
    
    # Status
    active = fields.Boolean(string='Active', default=True)
    
    @api.depends('name', 'doctor_id')
    def _compute_display_name(self):
        for doctor in self:
            doctor.display_name = f"Dr. {doctor.name} [{doctor.doctor_id}]"