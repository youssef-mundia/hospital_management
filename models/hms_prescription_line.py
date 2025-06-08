from odoo import models, fields, api, _

class HmsPrescriptionLine(models.Model):
    _name = 'hms.prescription.line'
    _description = 'Prescription Line'

    medical_record_id = fields.Many2one('hms.medical.record', string='Medical Record', required=True, ondelete='cascade')
    drug_id = fields.Many2one(
        'product.product', string='Drug', required=True,
        domain="[('is_medicine', '=', True), ('type', 'in', ['product', 'consu'])]",
        help="Select a drug. Ensure products are configured as storable/consumable and marked as medicine."
    )
    qty_prescribed = fields.Float(string='Quantity Prescribed', default=1.0, help="Quantity of the drug to be dispensed.")
    dosage = fields.Char(string='Dosage', help="e.g., 1 tablet, 10ml")
    frequency = fields.Char(string='Frequency', help="e.g., Twice a day, Every 6 hours")
    duration = fields.Char(string='Duration', help="e.g., 7 days, Until finished")
    notes = fields.Text(string='Notes')

    # Pour afficher le nom du médicament dans les vues tree/kanban si nécessaire
    name = fields.Char(related='drug_id.name', string="Drug Name", readonly=True, store=True)

    # Dispensation fields
    is_dispensed = fields.Boolean(string='Dispensed', default=False, copy=False, tracking=True)
    qty_dispensed = fields.Float(string='Quantity Dispensed', copy=False, tracking=True)
    dispense_date = fields.Datetime(string='Dispense Date', readonly=True, copy=False, tracking=True)
    dispensed_by_id = fields.Many2one('res.users', string='Dispensed By', readonly=True, copy=False)

    @api.onchange('drug_id')
    def _onchange_drug_id(self):
        if self.drug_id:
            # Vous pourriez pré-remplir des notes basées sur le médicament si nécessaire
            pass

    def action_dispense_drug(self):
        for line in self:
            if not line.is_dispensed:
                # La logique de création de mouvement de stock (stock.move) serait ajoutée ici
                # pour une gestion d'inventaire complète.
                # Pour l'instant, nous marquons seulement comme délivré.
                line.write({
                    'is_dispensed': True,
                    'qty_dispensed': line.qty_prescribed, # Par défaut, délivre la quantité prescrite
                    'dispense_date': fields.Datetime.now(),
                    'dispensed_by_id': self.env.user.id
                })
                line.medical_record_id.message_post(
                    body=_("Drug %s (%.2f units) for patient %s marked as dispensed by %s.") %
                         (line.drug_id.name, line.qty_dispensed, line.medical_record_id.patient_id.name, self.env.user.name)
                )
        return True