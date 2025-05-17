# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting
from datetime import datetime

class WebsiteSaleRentingCustom(WebsiteSaleRenting):
    @http.route('/rental/product/constraints', type='json', auth="public", methods=['POST'], website=True)
    def renting_product_constraints(self, **post):
        """
        Surcharge pour renvoyer une durée minimale dynamique en fonction de la date de référence.
        Si aucune date n'est fournie dans la requête, utilise la date actuelle.
        """
        from odoo import fields
        
        reference_date_str = post.get('start_date')
        reference_date = fields.Date.today()  # Valeur par défaut (date actuelle)
        
        if reference_date_str:
            # Liste des formats à essayer, incluant le format standard d'Odoo après serializeDateTime
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # Format standard Odoo (après serializeDateTime)
                '%Y-%m-%dT%H:%M:%S',  # Format ISO avec T
                '%Y-%m-%dT%H:%M:%S.%fZ',  # Format ISO complet avec millisecondes et Z
                '%Y-%m-%d',  # Date simple
            ]
            
            for date_format in formats_to_try:
                try:
                    reference_date = datetime.strptime(reference_date_str, date_format).date()
                    break
                except ValueError:
                    continue
        
        # Obtenir les données de durée minimale dynamique sous forme de dictionnaire
        minimal_time_data = request.env.company.get_dynamic_renting_minimal_duration(reference_date)
        
        # Extraire les valeurs du dictionnaire
        minimal_duration = minimal_time_data.get('duration', 0)
        minimal_unit = minimal_time_data.get('unit', 'day')
        start_date = minimal_time_data.get('start_date', None)
        end_date = minimal_time_data.get('end_date', None)
        
        weekdays = request.env.company._get_renting_forbidden_days()
        response = {
            'renting_unavailability_days': {day: day in weekdays for day in range(1, 8)},  # Corrigé 'renting_unavailabity_days' en 'renting_unavailability_days'
            'renting_minimal_time': {
                'duration': minimal_duration,
                'unit': minimal_unit,
                'start_date': start_date if start_date else '',
                'end_date': end_date if end_date else ''
            },
            'website_tz': request.website.tz,
        }
        return response
