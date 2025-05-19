from odoo import api, fields, models

class MBRentingPeriod(models.Model):
    _name = 'mb.renting.period'
    _description = 'Renting Period'
    _order = 'start_date'
    
    name = fields.Char('Nom', required=True)
    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    
    start_date = fields.Date('Start Date', required=True)
    end_date = fields.Date('End Date', required=True)

    is_closed = fields.Boolean('Closed', default=False)
    
    minimal_time_duration = fields.Integer('Minimum Duration', default=1)
    minimal_time_unit = fields.Selection([
        ('hour', 'Hour'), 
        ('day', 'Day'), 
        ('week', 'Week')
    ], string="Minimum Duration Unit", default='day', required=True)
    
    day_configs = fields.One2many('mb.renting.day.config', 'period_id', string='Day Configurations',
                                  domain="[('company_id', '=', company_id)]")
    
    # Relation inverse vers les configurations de stock
    stock_period_config_ids = fields.One2many(
        'mb.renting.stock.period.config',
        'period_id',
        string='Configurations de stock'
    )
    
    _sql_constraints = [
        ('date_check', 'CHECK(start_date <= end_date)', 'The start date must be before the end date.'),
        ('company_dates_unique', 'UNIQUE(company_id, start_date, end_date)', 'A period with these dates already exists.')
    ]
    @api.model
    def find_period_for_date(self, date, company_id=None):
        """Find the period corresponding to a date"""
        if not company_id:
            company_id = self.env.company.id
            
        return self.search([
            ('company_id', '=', company_id),
            ('start_date', '<=', date),
            ('end_date', '>=', date)
        ], limit=1)
