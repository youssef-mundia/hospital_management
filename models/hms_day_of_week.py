from odoo import models, fields

class HmsDayOfWeek(models.Model):
    _name = 'hms.day.of.week'
    _description = 'Day of the Week'
    _order = 'sequence'

    name = fields.Char(string='Day Name', required=True, translate=True)
    code = fields.Char(string='Day Code', required=True) # e.g., 'monday', 'tuesday'
    sequence = fields.Integer(string='Sequence', default=10, help="Used to order days")

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'Day code must be unique!'),
        ('name_uniq', 'unique (name)', 'Day name must be unique!')
    ]

    def __str__(self):
        return self.name