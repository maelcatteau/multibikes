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
    
    # On remplace la gestion de la durée minimale par une référence à sale.temporal.recurrence
    recurrence_id = fields.Many2one(
        'sale.temporal.recurrence',
        string='Récurrence de location',
        required=True,
        help="Règle de récurrence utilisée pour définir la durée minimale de location."
    )
    recurrence_name = fields.Char(related='recurrence_id.name', string="Nom de la récurrence", store=False, readonly=True)
    recurrence_duration = fields.Integer(related='recurrence_id.duration', string="Durée minimale", store=False, readonly=True)
    recurrence_unit = fields.Selection(related='recurrence_id.unit', string="Unité de durée", store=False, readonly=True)
    
    day_configs = fields.One2many('mb.renting.day.config', 'period_id', string='Day Configurations',
                                  domain="[('company_id', '=', company_id)]")
    
    # Relation inverse vers les configurations de stock
    stock_period_config_ids = fields.One2many(
        'mb.renting.stock.period.config',
        'period_id',
        string='Configurations de stock'
    )

    total_storable_products = fields.Integer(
        string='Produits stockables disponibles',
        compute='_compute_total_storable_products',
        help="Nombre total de produits stockables à configurer"
    )

    # Champ pour indiquer combien de produits restent à configurer
    remaining_products_to_configure = fields.Integer(
        string='Produits restants à configurer',
        compute='_compute_products_to_configure',
        store=False,
        help="Nombre de produits stockables qui n'ont pas encore été configurés"
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

    @api.depends()
    def _compute_total_storable_products(self):
        """Calcule le nombre total de produits stockables dans le système."""
        for period in self:
            domain = [('is_storable', '=', True)]
            if period.company_id:
                domain += ['|', ('company_id', '=', period.company_id.id), ('company_id', '=', False)]
            
            # Recherche tous les produits stockables selon le domaine
            product_count = self.env['product.product'].search_count(domain)
            period.total_storable_products = product_count

    @api.depends('stock_period_config_ids.storable_product_ids')
    def _compute_products_to_configure(self):
        """
        Calcule le nombre de produits stockables qui n'ont PAS encore été configurés.
        Ce sont les produits qui sont stockables mais qui ne figurent pas dans stock_period_config_ids.storable_product_ids.
        """
        for period in self:
            # Récupérer tous les produits stockables
            domain = [('is_storable', '=', True)]
            if period.company_id:
                domain += ['|', ('company_id', '=', period.company_id.id), ('company_id', '=', False)]
            all_storable_products = self.env['product.product'].search(domain)
            
            # Récupérer les IDs des produits déjà configurés pour cette période
            configured_product_ids = period.stock_period_config_ids.mapped('storable_product_ids').ids
            
            # Compter les produits non configurés
            unconfigured_count = 0
            for product in all_storable_products:
                if product.id not in configured_product_ids:
                    unconfigured_count += 1
            
            period.remaining_products_to_configure = unconfigured_count