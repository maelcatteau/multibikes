from odoo import api, fields, models
from datetime import date

class ResCompany(models.Model):
    _inherit = 'res.company'
    
    renting_periods = fields.One2many(
        'mb.renting.period', 
        'company_id', 
        string='Périodes de location'
    )
    
    @api.model
    def create(self, vals):
        """Initialize default periods when creating"""
        company = super().create(vals)
        self._create_default_renting_periods(company)
        return company
    
    def _create_default_renting_periods(self, company):
        """Create default periods for a new company"""
        today = fields.Date.today()
        year = today.year
        
        # Create three default periods
        periods = [
            {
                'name': 'Before season',
                'company_id': company.id,
                'start_date': fields.Date.to_string(date(year, 5, 1)),
                'end_date': fields.Date.to_string(date(year, 6, 31)),
                'minimal_time_duration': 1,
                'minimal_time_unit': 'day'
            },
            {
                'name': 'Season',
                'company_id': company.id,
                'start_date': fields.Date.to_string(date(year, 7, 1)),
                'end_date': fields.Date.to_string(date(year, 8, 31)),
                'minimal_time_duration': 3,
                'minimal_time_unit': 'day'
            },
            {
                'name': 'After season',
                'company_id': company.id,
                'start_date': fields.Date.to_string(date(year, 9, 1)),
                'end_date': fields.Date.to_string(date(year, 9, 30)),
                'minimal_time_duration': 1,
                'minimal_time_unit': 'day'
            }
        ]
        self.env['mb.renting.period'].create(periods)
    
    def _create_default_day_configs(self, company):
        """Créer les configurations par défaut pour tous les jours et périodes"""
        configs = []
        for period in ['1', '2', '3']:
            for day in range(7):  # 0-6 pour lundi à dimanche
                configs.append({
                    'company_id': company.id,
                    'period_number': period,
                    'day_of_week': str(day),
                    'is_open': True,
                    'allow_pickup': True,
                    'pickup_hour_from': 8.0,
                    'pickup_hour_to': 18.0,
                    'allow_return': True,
                    'return_hour_from': 8.0,
                    'return_hour_to': 18.0,
                })
        self.env['mb.renting.day.config'].create(configs)
