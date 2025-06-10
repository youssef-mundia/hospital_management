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

    image = fields.Image(string="Photo")

    specialization = fields.Char(string='Specialization', tracking=True)
    license_number = fields.Char(string='License Number', tracking=True)
    experience_years = fields.Integer(string='Experience (Years)', tracking=True)
    qualification = fields.Text(string='Qualification')

    phone = fields.Char(string='Phone', tracking=True)
    mobile = fields.Char(string='Mobile', tracking=True)
    email = fields.Char(string='Email', tracking=True)

    department_id = fields.Many2one('hms.department', string='Department', tracking=True)

    consultation_fee = fields.Float(string='Consultation Fee')

    available_days = fields.Many2many('hms.day.of.week', string='Available Days')

    appointment_ids = fields.One2many('hms.appointment', 'doctor_id', string='Appointments')
    user_id = fields.Many2one('res.users', string='Related User', tracking=True)

    active = fields.Boolean(string='Active', default=True, tracking=True)

    @api.depends('name', 'doctor_id')
    def _compute_display_name(self):
        for doctor in self:
            doc_id_str = doctor.doctor_id if doctor.doctor_id else ""
            doc_name_str = doctor.name if doctor.name else ""
            if doc_id_str and doc_name_str:
                doctor.display_name = f"Dr. {doc_name_str} [{doc_id_str}]"
            elif doc_name_str:
                doctor.display_name = f"Dr. {doc_name_str}"
            else:
                doctor.display_name = ""