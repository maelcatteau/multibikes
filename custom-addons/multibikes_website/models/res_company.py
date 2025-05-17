from odoo import api, fields, models
from datetime import date

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    renting_periods = fields.One2many(
        'mb.renting.period', 
        'company_id', 
        string='Périodes de location'
    )


    def get_dynamic_renting_minimal_duration(self, reference_date=None):
        """
        Calcule la durée minimale de location en fonction de la date de référence.
        Retourne un dictionnaire contenant la durée, l'unité, et les dates de début et de fin.
        """
        self.ensure_one()
        if not reference_date:
            reference_date = fields.Date.today()

        # Logique pour déterminer la durée minimale (exemple)
        duration = 1  # Valeur par défaut ou calculée
        unit = 'day'
        start_date = None
        end_date = None

        # Recherche des périodes correspondant à la date de référence
        period = self.env['mb.renting.period'].search([
            ('company_id', '=', self.id),
            ('start_date', '<=', reference_date),
            ('end_date', '>=', reference_date)
        ], limit=1)

        if period:
            duration = period.minimal_time_duration
            unit = period.minimal_time_unit
            start_date = period.start_date
            end_date = period.end_date

        return {
            'duration': duration,
            'unit': unit,
            'start_date': start_date,
            'end_date': end_date
        }