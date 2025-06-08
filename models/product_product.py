from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_medicine = fields.Boolean(
        related='product_tmpl_id.is_medicine',
        store=True,
        readonly=True,
        string="Is a Medicine"
    )