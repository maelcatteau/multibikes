from odoo import api, fields, models

class MBRentingDayConfig(models.Model):
    _name = 'mb.renting.day.config'
    _description = 'Day Configuration for Renting'
    
    period_id = fields.Many2one('mb.renting.period', required=True, ondelete='cascade', string='Période')
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade', string='Société')
    
    day_of_week = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], required=True)
    
    is_open = fields.Boolean('Day Open', default=True)
    
    allow_pickup = fields.Boolean('Pickup Allowed', default=True)
    pickup_hour_from = fields.Float('Pickup From', default=9.45)
    pickup_hour_to = fields.Float('Pickup To', default=14.15)
    
    allow_return = fields.Boolean('Return Allowed', default=True)
    return_hour_from = fields.Float('Return From', default=17.30)
    return_hour_to = fields.Float('Return To', default=18.30)
    
    
    @api.onchange('is_open')
    def _onchange_is_open(self):
        """Quand is_open passe à False, désactive les options de pickup et return et réinitialise les horaires"""
        if not self.is_open:
            self.allow_pickup = False
            self.allow_return = False
            self.pickup_hour_from = False
            self.pickup_hour_to = False
            self.return_hour_from = False
            self.return_hour_to = False
    
    @api.model
    def get_config_for_date(self, date, company_id=None):
        """Get the configuration for a specific date"""
        if not company_id:
            company_id = self.env.company.id
            
        # Determine the period to which the date belongs
        period = self.env['mb.renting.period'].find_period_for_date(date, company_id)
        
        if not period:
            return None
            
        # Get the configuration for the day of the week
        weekday = date.weekday()  # 0-6 (Monday-Sunday)
        return self.search([
            ('company_id', '=', company_id),
            ('period_id', '=', period.id),
            ('day_of_week', '=', str(weekday))
        ], limit=1)
    
    def is_pickup_allowed(self, hour=None):
        """Check if pickup is allowed for this day/hour"""
        if not self.is_open or not self.allow_pickup:
            return False
        if hour is not None:
            return self.pickup_hour_from <= hour <= self.pickup_hour_to
        return True
        
    def is_return_allowed(self, hour=None):
        """Check if return is allowed for this day/hour"""
        if not self.is_open or not self.allow_return:
            return False
        if hour is not None:
            return self.return_hour_from <= hour <= self.return_hour_to
        return True
