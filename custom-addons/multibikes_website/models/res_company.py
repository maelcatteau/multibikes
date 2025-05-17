from odoo import models, fields, api

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Vos champs pour les périodes saisonnières (comme dans votre code initial)
    mb_renting_period1_start_date = fields.Date(string="Date début période 1", default=lambda self: fields.Date.today().replace(month=1, day=1))
    mb_renting_period1_end_date = fields.Date(string="Date fin période 1", default=lambda self: fields.Date.today().replace(month=4, day=30))
    mb_renting_period1_minimal_time_duration = fields.Integer(string="Durée minimale période 1", default=1)
    mb_renting_period1_minimal_time_unit = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
        ('week', 'Week')], string="Unité de durée période 1", default='day')
    
    # Ajoutez les périodes 2 et 3 comme dans votre code
    mb_renting_period2_start_date = fields.Date(string="Date début période 2", default=lambda self: fields.Date.today().replace(month=5, day=1))
    mb_renting_period2_end_date = fields.Date(string="Date fin période 2", default=lambda self: fields.Date.today().replace(month=8, day=31))
    mb_renting_period2_minimal_time_duration = fields.Integer(string="Durée minimale période 2", default=1)
    mb_renting_period2_minimal_time_unit = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
        ('week', 'Week')], string="Unité de durée période 2", default='day')
    
    mb_renting_period3_start_date = fields.Date(string="Date début période 3", default=lambda self: fields.Date.today().replace(month=9, day=1))
    mb_renting_period3_end_date = fields.Date(string="Date fin période 3", default=lambda self: fields.Date.today().replace(month=12, day=31))
    mb_renting_period3_minimal_time_duration = fields.Integer(string="Durée minimale période 3", default=1)
    mb_renting_period3_minimal_time_unit = fields.Selection([
        ('hour', 'Hour'),
        ('day', 'Day'),
        ('week', 'Week')], string="Unité de durée période 3", default='day')

    def get_dynamic_renting_minimal_duration(self, reference_date=None):
        """
        Calcule la durée minimale de location en fonction de la date de référence.
        Si aucune date n'est fournie, utilise la date actuelle.
        Retourne un dictionnaire contenant la durée, l'unité, et les dates de début et de fin de la période applicable.
        """
        self.ensure_one()

        if not reference_date:
            reference_date = fields.Date.today()

        # Vérifier la période 1 si les dates sont définies
        if self.mb_renting_period1_start_date and self.mb_renting_period1_end_date:
            try:
                if self.mb_renting_period1_start_date <= reference_date <= self.mb_renting_period1_end_date:
                    return {
                        'duration': self.mb_renting_period1_minimal_time_duration,
                        'unit': self.mb_renting_period1_minimal_time_unit,
                        'start_date': self.mb_renting_period1_start_date,
                        'end_date': self.mb_renting_period1_end_date
                    }
            except TypeError:
                pass

        # Vérifier la période 2 si les dates sont définies
        if self.mb_renting_period2_start_date and self.mb_renting_period2_end_date:
            try:
                if self.mb_renting_period2_start_date <= reference_date <= self.mb_renting_period2_end_date:
                    return {
                        'duration': self.mb_renting_period2_minimal_time_duration,
                        'unit': self.mb_renting_period2_minimal_time_unit,
                        'start_date': self.mb_renting_period2_start_date,
                        'end_date': self.mb_renting_period2_end_date
                    }
            except TypeError:
                pass

        # Vérifier la période 3 si les dates sont définies
        if self.mb_renting_period3_start_date and self.mb_renting_period3_end_date:
            try:
                if self.mb_renting_period3_start_date <= reference_date <= self.mb_renting_period3_end_date:
                    return {
                        'duration': self.mb_renting_period3_minimal_time_duration,
                        'unit': self.mb_renting_period3_minimal_time_unit,
                        'start_date': self.mb_renting_period3_start_date,
                        'end_date': self.mb_renting_period3_end_date
                    }
            except TypeError:
                pass

        # Si aucune période ne correspond, retourner la valeur par défaut sans dates de période
        return {
            'duration': self.renting_minimal_time_duration,
            'unit': self.renting_minimal_time_unit,
            'start_date': None,
            'end_date': None
        }
