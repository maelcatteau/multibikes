# -*- coding: utf-8 -*-

from odoo import api, fields, models

class MBRentingDayConfig(models.Model):
    """Configuration des jours de location par période"""
    _name = 'mb.renting.day.config'
    _description = 'Configuration des jours pour la location'
    _order = 'period_id, day_of_week'
    
    # === CHAMPS PRINCIPAUX ===
    period_id = fields.Many2one(
        'mb.renting.period', 
        required=True, 
        ondelete='cascade', 
        string='Période'
    )
    company_id = fields.Many2one(
        'res.company', 
        required=True, 
        ondelete='cascade', 
        string='Société'
    )
    
    day_of_week = fields.Selection([
        ('1', 'Lundi'),
        ('2', 'Mardi'), 
        ('3', 'Mercredi'),
        ('4', 'Jeudi'),
        ('5', 'Vendredi'),
        ('6', 'Samedi'),
        ('7', 'Dimanche')
    ], required=True, string='Jour de la semaine')
    
    # === CONFIGURATION GÉNÉRALE ===
    is_open = fields.Boolean('Jour ouvert', default=True)
    
    # === CONFIGURATION PICKUP ===
    allow_pickup = fields.Boolean('Pickup autorisé', default=True)
    pickup_hour_from = fields.Float('Pickup de', default=9.75)  # 9h45
    pickup_hour_to = fields.Float('Pickup à', default=14.25)   # 14h15
    
    # === CONFIGURATION RETOUR ===
    allow_return = fields.Boolean('Retour autorisé', default=True)
    return_hour_from = fields.Float('Retour de', default=17.50)  # 17h30
    return_hour_to = fields.Float('Retour à', default=18.50)     # 18h30

    # === CONTRAINTES SQL ===
    _sql_constraints = [
        ('pickup_hours_logic', 
         'CHECK (allow_pickup = false OR pickup_hour_from < pickup_hour_to)', 
         "L'heure de début de pickup doit être antérieure à l'heure de fin"),
        ('return_hours_logic', 
         'CHECK (allow_return = false OR return_hour_from < return_hour_to)', 
         "L'heure de début de retour doit être antérieure à l'heure de fin"),
        ('unique_day_per_period', 
         'UNIQUE (period_id, company_id, day_of_week)', 
         "Un seul config par jour et par période autorisé"),
    ]
    
    def __str__(self):
        """
        Définit l'affichage textuel de l'objet
        - Au lieu de voir: <mb.renting.day.config(42,)> 
        - On verra: "Période Été 2024 - Lundi"
        - Utile dans les logs, sélecteurs, debugger, etc.
        """
        day_names = dict(self._fields['day_of_week'].selection)
        return f"{self.period_id.name} - {day_names.get(self.day_of_week)}"
    
    # === MÉTHODES ONCHANGE ===
    @api.onchange('is_open')
    def _onchange_is_open(self):
        """Quand le jour est fermé, désactive tout et réinitialise les horaires"""
        if not self.is_open:
            self.allow_pickup = False
            self.allow_return = False
            self.pickup_hour_from = False
            self.pickup_hour_to = False
            self.return_hour_from = False
            self.return_hour_to = False

    @api.onchange('allow_pickup')
    def _onchange_allow_pickup(self):
        """Quand pickup est désactivé, réinitialise ses horaires"""
        if not self.allow_pickup:
            self.pickup_hour_from = False
            self.pickup_hour_to = False
    
    @api.onchange('allow_return')
    def _onchange_allow_return(self):
        """Quand retour est désactivé, réinitialise ses horaires"""
        if not self.allow_return:
            self.return_hour_from = False
            self.return_hour_to = False
    
    # === MÉTHODES MÉTIER ===
    @api.model
    def get_config_for_date(self, date):
        """Récupère la configuration pour une date donnée"""
            
        # Trouve la période correspondant à la date
        period = self.env['mb.renting.period'].find_period_for_date(date)
        if not period:
            return None
            
        # Conversion : date.weekday() retourne 0-6, nos sélections sont 1-7
        weekday = str(date.weekday() + 1)  # Lundi=1, ..., Dimanche=7
        
        return self.search([
            ('company_id', '=', self.env.company.id),
            ('period_id', '=', period.id),
            ('day_of_week', '=', weekday)
        ], limit=1)
    
    def is_pickup_allowed(self, hour=None):
        """Vérifie si le pickup est autorisé pour ce jour/heure"""
        if not self.is_open or not self.allow_pickup:
            return False
        if hour is not None:
            return self.pickup_hour_from <= hour <= self.pickup_hour_to
        return True
        
    def is_return_allowed(self, hour=None):
        """Vérifie si le retour est autorisé pour ce jour/heure"""
        if not self.is_open or not self.allow_return:
            return False
        if hour is not None:
            return self.return_hour_from <= hour <= self.return_hour_to
        return True
