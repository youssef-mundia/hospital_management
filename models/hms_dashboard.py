from odoo import models, fields, api
from datetime import datetime, timedelta, date
import calendar


class HmsDashboard(models.TransientModel):
    _name = 'hms.dashboard'
    _description = 'HMS Dashboard Statistics'


    total_patients = fields.Integer(string='Total Patients', compute='_compute_dashboard_stats')
    new_patients_month = fields.Integer(string='New Patients This Month', compute='_compute_dashboard_stats')
    total_doctors = fields.Integer(string='Total Doctors', compute='_compute_dashboard_stats')
    today_appointments = fields.Integer(string="Today's Appointments", compute='_compute_dashboard_stats')
    month_appointments = fields.Integer(string='Monthly Appointments', compute='_compute_dashboard_stats')
    pending_prescriptions = fields.Integer(string='Pending Prescriptions', compute='_compute_dashboard_stats')
    monthly_revenue = fields.Float(string='Monthly Revenue', compute='_compute_dashboard_stats')
    completion_rate = fields.Float(string='Completion Rate', compute='_compute_dashboard_stats')

    medical_records_month = fields.Integer(string='Medical Records This Month', compute='_compute_dashboard_stats')
    follow_up_required = fields.Integer(string='Follow-up Required', compute='_compute_dashboard_stats')
    department_count = fields.Integer(string='Total Departments', compute='_compute_dashboard_stats')
    dispensing_rate = fields.Float(string='Dispensing Rate', compute='_compute_dashboard_stats')

    @api.depends()
    def _compute_dashboard_stats(self):
        """Compute all dashboard statistics"""
        for record in self:
            today = fields.Date.today()
            month_start = today.replace(day=1)

            record.total_patients = self.env['hms.patient'].search_count([('active', '=', True)])
            record.new_patients_month = self.env['hms.patient'].search_count([
                ('create_date', '>=', month_start),
                ('active', '=', True)
            ])
            record.total_doctors = self.env['hms.doctor'].search_count([('active', '=', True)])

            record.today_appointments = self.env['hms.appointment'].search_count([
                ('appointment_date', '>=', today.strftime('%Y-%m-%d 00:00:00')),
                ('appointment_date', '<=', today.strftime('%Y-%m-%d 23:59:59'))
            ])

            record.month_appointments = self.env['hms.appointment'].search_count([
                ('appointment_date', '>=', month_start.strftime('%Y-%m-%d 00:00:00'))
            ])

            record.pending_prescriptions = self.env['hms.prescription.line'].search_count([
                ('state', '=', 'pending')
            ])

            next_month = month_start + timedelta(days=32)
            next_month = next_month.replace(day=1)

            invoices = self.env['account.move'].search([
                ('create_date', '>=', month_start),
                ('create_date', '<', next_month),
                ('move_type', '=', 'out_invoice'),
                ('state', '!=', 'cancel')
            ])
            record.monthly_revenue = sum(invoice.amount_total for invoice in invoices)

            completed_appointments = self.env['hms.appointment'].search_count([
                ('appointment_date', '>=', month_start.strftime('%Y-%m-%d 00:00:00')),
                ('state', '=', 'completed')
            ])
            record.completion_rate = round(
                (completed_appointments / record.month_appointments * 100), 1
            ) if record.month_appointments > 0 else 0

            record.medical_records_month = self.env['hms.medical.record'].search_count([
                ('date', '>=', month_start.strftime('%Y-%m-%d 00:00:00'))
            ])

            record.follow_up_required = self.env['hms.medical.record'].search_count([
                ('follow_up_required', '=', True),
                ('date', '>=', month_start.strftime('%Y-%m-%d 00:00:00'))
            ])

            record.department_count = self.env['hms.department'].search_count([('active', '=', True)])

            total_prescriptions = self.env['hms.prescription.line'].search_count([
                ('prescription_date', '>=', month_start.strftime('%Y-%m-%d 00:00:00'))
            ])
            dispensed_prescriptions = self.env['hms.prescription.line'].search_count([
                ('prescription_date', '>=', month_start.strftime('%Y-%m-%d 00:00:00')),
                ('state', '=', 'dispensed')
            ])
            record.dispensing_rate = round(
                (dispensed_prescriptions / total_prescriptions * 100), 1
            ) if total_prescriptions > 0 else 0

    def refresh_dashboard(self):
        """Refresh dashboard data"""
        self._compute_dashboard_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def default_get(self, fields_list):
        """Override to always create a new record with fresh data"""
        result = super().default_get(fields_list)
        return result