from odoo import api, fields, models, _
from datetime import timedelta

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    # Période 1 (Basse saison)
    renting_period1_start_date = fields.Date(string="Date début période 1", default=lambda self: fields.Date.today().replace(month=1, day=1))
    renting_period1_end_date = fields.Date(string="Date fin période 1", default=lambda self: fields.Date.today().replace(month=4, day=30))
    renting_period1_minimal_time_duration = fields.Integer(string="Durée minimale période 1", default=1)
    renting_period1_minimal_time_unit = fields.Selection([
        ('hour', 'Heures'),
        ('day', 'Jours'),
        ('week', 'Semaine')], string="Unité de durée période 1", default='day')
    
    # Période 2 (Moyenne saison)
    renting_period2_start_date = fields.Date(string="Date début période 2", default=lambda self: fields.Date.today().replace(month=5, day=1))
    renting_period2_end_date = fields.Date(string="Date fin période 2", default=lambda self: fields.Date.today().replace(month=6, day=30))
    renting_period2_minimal_time_duration = fields.Integer(string="Durée minimale période 2", default=2)
    renting_period2_minimal_time_unit = fields.Selection([
        ('hour', 'Heures'),
        ('day', 'Jours'),
        ('week', 'Semaine')], string="Unité de durée période 2", default='day')
    
    # Période 3 (Haute saison)
    renting_period3_start_date = fields.Date(string="Date début période 3", default=lambda self: fields.Date.today().replace(month=7, day=1))
    renting_period3_end_date = fields.Date(string="Date fin période 3", default=lambda self: fields.Date.today().replace(month=8, day=31))
    renting_period3_minimal_time_duration = fields.Integer(string="Durée minimale période 3", default=3)
    renting_period3_minimal_time_unit = fields.Selection([
        ('hour', 'Hours'),
        ('day', 'Days'),
        ('week', 'Weeks')], string="Unité de durée période 3", default='day')

    @api.model
    def get_minimal_rental_duration(self, rental_date):
        """Calcule la durée minimale de location en fonction de la date"""
        self.ensure_one()
        date_to_check = fields.Date.from_string(rental_date)
        
        # Vérifier à quelle période appartient la date
        if self.renting_period1_start_date <= date_to_check <= self.renting_period1_end_date:
            duration = self.renting_period1_minimal_time_duration
            unit = self.renting_period1_minimal_time_unit
        elif self.renting_period2_start_date <= date_to_check <= self.renting_period2_end_date:
            duration = self.renting_period2_minimal_time_duration
            unit = self.renting_period2_minimal_time_unit
        elif self.renting_period3_start_date <= date_to_check <= self.renting_period3_end_date:
            duration = self.renting_period3_minimal_time_duration
            unit = self.renting_period3_minimal_time_unit
        else:
            # Utiliser la durée par défaut si aucune période ne correspond
            duration = self.renting_minimal_time_duration
            unit = self.renting_minimal_time_unit
            
        return duration, unit

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    # Période 1 (Basse saison)
    renting_period1_start_date = fields.Date(
        related='company_id.renting_period1_start_date', readonly=False, 
        string="Date de début - Basse saison")
    renting_period1_end_date = fields.Date(
        related='company_id.renting_period1_end_date', readonly=False,
        string="Date de fin - Basse saison")
    renting_period1_minimal_time_duration = fields.Integer(
        related='company_id.renting_period1_minimal_time_duration', readonly=False,
        string="Durée minimum - Basse saison")
    renting_period1_minimal_time_unit = fields.Selection(
        related='company_id.renting_period1_minimal_time_unit', readonly=False,
        string="Unité - Basse saison")
    
    # Période 2 (Moyenne saison)
    renting_period2_start_date = fields.Date(
        related='company_id.renting_period2_start_date', readonly=False,
        string="Date de début - Moyenne saison")
    renting_period2_end_date = fields.Date(
        related='company_id.renting_period2_end_date', readonly=False,
        string="Date de fin - Moyenne saison")
    renting_period2_minimal_time_duration = fields.Integer(
        related='company_id.renting_period2_minimal_time_duration', readonly=False,
        string="Durée minimum - Moyenne saison")
    renting_period2_minimal_time_unit = fields.Selection(
        related='company_id.renting_period2_minimal_time_unit', readonly=False,
        string="Unité - Moyenne saison")
    
    # Période 3 (Haute saison)
    renting_period3_start_date = fields.Date(
        related='company_id.renting_period3_start_date', readonly=False,
        string="Date de début - Haute saison")
    renting_period3_end_date = fields.Date(
        related='company_id.renting_period3_end_date', readonly=False,
        string="Date de fin - Haute saison")
    renting_period3_minimal_time_duration = fields.Integer(
        related='company_id.renting_period3_minimal_time_duration', readonly=False,
        string="Durée minimum - Haute saison")
    renting_period3_minimal_time_unit = fields.Selection(
        related='company_id.renting_period3_minimal_time_unit', readonly=False,
        string="Unité - Haute saison")
