from odoo import models, fields


class HmsDepartment(models.Model):
    _name = 'hms.department'
    _description = 'Hospital Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Department Name', required=True, tracking=True)
    code = fields.Char(string='Department Code', required=True, tracking=True)
    description = fields.Text(string='Description')
    head_doctor_id = fields.Many2one('hms.doctor', string='Head of Department')
    
    # Relations
    doctor_ids = fields.One2many('hms.doctor', 'department_id', string='Doctors')
    
    # Status
    active = fields.Boolean(string='Active', default=True)