from odoo import models, fields


class HmsPatientInsurance(models.Model):
    _name = 'hms.patient.insurance'
    _description = 'Patient Insurance Details'
    _order = 'coverage_end_date desc, id desc'

    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, ondelete='cascade')
    insurance_company_id = fields.Many2one('res.partner', string='Insurance Company', required=True,
                                           domain="[('is_company', '=', True)]")
    policy_number = fields.Char(string='Policy Number', required=True)
    coverage_start_date = fields.Date(string='Coverage Start Date')
    coverage_end_date = fields.Date(string='Coverage End Date')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('policy_number_patient_uniq', 'unique (policy_number, patient_id, insurance_company_id)',
         'Policy number must be unique per patient and insurance company!')
    ]