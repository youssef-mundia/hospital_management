from odoo import models, fields, api
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
    appointment_date = fields.Datetime(string='Appointment Date & Time', required=True, tracking=True)
    duration = fields.Float(string='Duration (Hours)', default=1.0)
    end_datetime = fields.Datetime(string='End Date & Time', compute='_compute_end_datetime', store=True)
    
    # Details
    reason = fields.Text(string='Reason for Visit')
    notes = fields.Text(string='Notes')
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # Relations
    medical_record_ids = fields.One2many('hms.medical.record', 'appointment_id', string='Medical Records')
    
    @api.depends('name', 'patient_id', 'doctor_id')
    def _compute_display_name(self):
        for appointment in self:
            appointment.display_name = f"{appointment.name} - {appointment.patient_id.name} with Dr. {appointment.doctor_id.name}"
    
    @api.depends('appointment_date', 'duration')
    def _compute_end_datetime(self):
        for appointment in self:
            if appointment.appointment_date and appointment.duration:
                appointment.end_datetime = appointment.appointment_date + timedelta(hours=appointment.duration)
            else:
                appointment.end_datetime = False
    
    def action_confirm(self):
        self.state = 'confirmed'
    
    def action_start(self):
        self.state = 'in_progress'
    
    def action_complete(self):
        self.state = 'completed'
    
    def action_cancel(self):
        self.state = 'cancelled'