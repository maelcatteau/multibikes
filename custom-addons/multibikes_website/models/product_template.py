# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import format_amount
from math import ceil
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """
        Surcharge de la méthode pour :
        1. Filtrer les tarifs affichés dans la pricing_table en fonction de mb_website_published
        2. Ajouter la durée minimale dynamique basée sur la date
        """
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not product_or_template.rent_ok:
            return res

        # Récupération des objets
        currency = website.currency_id
        pricelist = website.pricelist_id
        ProductPricing = self.env['product.pricing']

        # Récupérer les dates du contexte ou de la commande
        order = website.sale_get_order() if website and request else self.env['sale.order']
        start_date_str = self.env.context.get('start_date')
        start_date = start_date_str or order.rental_start_date

        _logger.info("Calcul de la durée minimale pour date: %s", start_date)

        # Calcul de la durée minimale dynamique
        if start_date:
            try:
                if isinstance(start_date, str):
                    from datetime import datetime
                    start_date = datetime.strptime(start_date.split(" ")[0], "%Y-%m-%d").date()
                minimal_duration, minimal_unit = self.env.company.get_dynamic_renting_minimal_duration(start_date)
                _logger.info("Durée minimale calculée: %s %s", minimal_duration, minimal_unit)
                res['renting_minimal_duration'] = minimal_duration
                res['renting_minimal_unit'] = minimal_unit
            except Exception as e:
                _logger.error("Erreur lors du calcul de la durée minimale: %s", e)

        # Obtenir le tarif par défaut
        pricing = ProductPricing._get_first_suitable_pricing(product_or_template, pricelist)
        if not pricing:
            return res

        # Détermination des dates et de la durée de location
        start_date = self.env.context.get('start_date') or order.rental_start_date
        end_date = self.env.context.get('end_date') or order.rental_return_date
        if start_date and end_date:
            current_pricing = product_or_template._get_best_pricing_rule(
                start_date=start_date,
                end_date=end_date,
                pricelist=pricelist,
                currency=currency,
            )
            current_unit = current_pricing.recurrence_id.unit
            current_duration = ProductPricing._compute_duration_vals(start_date, end_date)[current_unit]
        else:
            current_unit = pricing.recurrence_id.unit
            current_duration = pricing.recurrence_id.duration
            current_pricing = pricing

        # Calcul du prix courant
        current_price = pricelist._get_product_price(
            product=product_or_template,
            quantity=quantity,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
        )

        default_start_date, default_end_date = self._get_default_renting_dates(
            start_date, end_date, current_duration, current_unit
        )

        from odoo.addons.sale_renting.models.product_pricing import PERIOD_RATIO
        ratio = ceil(current_duration) / pricing.recurrence_id.duration if pricing.recurrence_id.duration else 1
        if current_unit != pricing.recurrence_id.unit:
            ratio *= PERIOD_RATIO[current_unit] / PERIOD_RATIO[pricing.recurrence_id.unit]

        # Application des taxes
        product_taxes = res['product_taxes']
        if product_taxes:
            current_price = self.env['product.template']._apply_taxes_to_price(
                current_price, currency, product_taxes, res['taxes'], product_or_template,
            )

        # Filtrer les tarifs publiés
        all_suitable_pricings = ProductPricing._get_suitable_pricings(product_or_template, pricelist)
        published_pricings = all_suitable_pricings.filtered(lambda p: p.mb_website_published)

        if not published_pricings:
            pricing_table = []
        else:
            # Garder le tarif le plus bas par recurrence
            best_pricings = {}
            for p in published_pricings:
                if p.recurrence_id not in best_pricings or best_pricings[p.recurrence_id].price > p.price:
                    best_pricings[p.recurrence_id] = p

            published_pricings = best_pricings.values()

            def _pricing_price(pricing):
                price = self.env['product.template']._apply_taxes_to_price(
                    pricing.price, currency, product_taxes, res['taxes'], product_or_template
                ) if product_taxes else pricing.price

                if pricing.currency_id == currency:
                    return price

                return pricing.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                )

            pricing_table = [
                (p.name, format_amount(self.env, _pricing_price(p), currency))
                for p in published_pricings
            ]

        recurrence = pricing.recurrence_id

        return {
            **res,
            'is_rental': True,
            'rental_duration': recurrence.duration,
            'rental_duration_unit': recurrence.unit,
            'rental_unit': recurrence._get_unit_label(recurrence.duration),
            'default_start_date': default_start_date,
            'default_end_date': default_end_date,
            'current_rental_duration': ceil(current_duration),
            'current_rental_unit': current_pricing.recurrence_id._get_unit_label(current_duration),
            'current_rental_price': current_price,
            'current_rental_price_per_unit': current_price / (ratio or 1),
            'base_unit_price': 0,
            'base_unit_name': False,
            'pricing_table': pricing_table,
            'prevent_zero_price_sale': website.prevent_zero_price_sale and currency.is_zero(current_price),
        }
