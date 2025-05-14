# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting
from datetime import datetime
import logging

class WebsiteSaleRentingCustom(WebsiteSaleRenting):
    @http.route('/rental/product/constraints', type='json', auth="public", methods=['POST'], website=True)
    def renting_product_constraints(self, **post):
        """
        Surcharge pour renvoyer une durée minimale dynamique en fonction de la date de référence.
        Si aucune date n'est fournie dans la requête, utilise la date actuelle.
        """
        from odoo import fields
        _logger = logging.getLogger(__name__)
        
        # Log de débogage pour voir ce qui est reçu
        _logger.info("Requête de contraintes de location reçue avec données: %s", post)
        
        reference_date_str = post.get('start_date')
        reference_date = fields.Date.today()  # Valeur par défaut (date actuelle)
        
        if reference_date_str:
            _logger.info("Date de référence reçue: %s", reference_date_str)
            # Liste des formats à essayer, incluant le format standard d'Odoo après serializeDateTime
            formats_to_try = [
                '%Y-%m-%d %H:%M:%S',  # Format standard Odoo (après serializeDateTime)
                '%Y-%m-%dT%H:%M:%S',  # Format ISO avec T
                '%Y-%m-%dT%H:%M:%S.%fZ',  # Format ISO complet avec millisecondes et Z
                '%Y-%m-%d',  # Date simple
            ]
            
            for date_format in formats_to_try:
                try:
                    _logger.info("Essai de conversion avec format: %s", date_format)
                    reference_date = datetime.strptime(reference_date_str, date_format).date()
                    _logger.info("Format reconnu: %s, Date convertie: %s", date_format, reference_date)
                    break
                except ValueError:
                    continue
            else:
                _logger.warning("Aucun format ne correspond à la date reçue: %s, utilisation de la date par défaut: %s", reference_date_str, reference_date)
        
        _logger.info("Date de référence utilisée pour le calcul: %s", reference_date)
        
        # Calculer la durée minimale dynamique
        minimal_duration, minimal_unit = request.env.company.get_dynamic_renting_minimal_duration(reference_date)
        _logger.info("Durée minimale calculée: %s %s", minimal_duration, minimal_unit)

        weekdays = request.env.company._get_renting_forbidden_days()
        response = {
            'renting_unavailabity_days': {day: day in weekdays for day in range(1, 8)},
            'renting_minimal_time': {
                'duration': minimal_duration,
                'unit': minimal_unit,
            },
            'website_tz': request.website.tz,
        }
        _logger.info("Réponse envoyée: %s", response)
        return response
