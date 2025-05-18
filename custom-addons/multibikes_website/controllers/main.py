# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting
from datetime import datetime, timedelta, date
import json
from odoo import fields

class WebsiteSaleRentingCustom(WebsiteSaleRenting):
    @http.route('/rental/product/constraints', type='json', auth="public", methods=['POST'], website=True)
    def renting_product_constraints(self, **post):
        """
        Renvoie toutes les informations des périodes et configurations pour les trois prochaines années.
        """
        
        
        # Obtenir la date actuelle
        today = fields.Date.today()
        
        # Calculer la date limite (3 ans à partir d'aujourd'hui)
        end_date = today + timedelta(days=3*365)
        
        # Récupérer toutes les périodes pour les 3 prochaines années
        periods = request.env['mb.renting.period'].search([
            ('company_id', '=', request.env.company.id),
            ('end_date', '>=', today),
            ('start_date', '<=', end_date)
        ])
        
        # Préparer les données des périodes
        periods_data = []
        for period in periods:
            # Récupérer les configurations de jours pour cette période
            day_configs = {}
            for config in period.day_configs:
                day_configs[config.day_of_week] = {
                    'is_open': config.is_open,
                    'allow_pickup': config.allow_pickup,
                    'pickup_hour_from': config.pickup_hour_from,
                    'pickup_hour_to': config.pickup_hour_to,
                    'allow_return': config.allow_return,
                    'return_hour_from': config.return_hour_from,
                    'return_hour_to': config.return_hour_to
                }
            
            periods_data.append({
                'id': period.id,
                'name': period.name,
                'start_date': fields.Date.to_string(period.start_date),
                'end_date': fields.Date.to_string(period.end_date),
                'is_closed': period.is_closed,
                'minimal_time_duration': period.minimal_time_duration,
                'minimal_time_unit': period.minimal_time_unit,
                'day_configs': day_configs
            })
        
        weekdays = request.env.company._get_renting_forbidden_days()
        
        # Construire la réponse
        response = {
            'all_periods': periods_data,
        }
        
        return response
