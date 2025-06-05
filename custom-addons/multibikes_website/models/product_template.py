# -*- coding: utf-8 -*-
"""Model Product Template for Multibikes Website Module."""
import logging
from math import ceil
from odoo import models
from odoo.tools import format_amount
from odoo.http import request
from odoo.addons.sale_renting.models.product_pricing import PERIOD_RATIO

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template,
                                          quantity, date, website):
        """
        Surcharge de la méthode pour :
        1. Filtrer les tarifs affichés dans la pricing_table
          en fonction de mb_website_published
        2. Calculer la quantité disponible en fonction des dates de début et de fin
        """
        res = super()._get_additionnal_combination_info(
            product_or_template, quantity, date, website
            )

        if not product_or_template.rent_ok:
            return res

        # Récupération des objets
        currency = website.currency_id
        pricelist = website.pricelist_id
        product_pricing = self.env['product.pricing']

        # Obtenir le tarif par défaut
        pricing = product_pricing._get_first_suitable_pricing(
            product_or_template, pricelist)
        if not pricing:
            return res

        # Récupérer les dates du contexte ou de la commande
        order = (
            website.sale_get_order() if website and request else self.env['sale.order']
        )
        start_date = self.env.context.get('start_date') or order.rental_start_date
        end_date = self.env.context.get('end_date') or order.rental_return_date

        # Convertir les dates en objets datetime naïfs
        if start_date:
            start_date = start_date.replace(tzinfo=None)
        if end_date:
            end_date = end_date.replace(tzinfo=None)

        # Calcul de la quantité disponible
        free_qty = self.calculate_min_availability_over_period(
            product_or_template, start_date, end_date)
        # Détermination des dates et de la durée de location
        if start_date and end_date:
            current_pricing = product_or_template._get_best_pricing_rule(
                start_date=start_date,
                end_date=end_date,
                pricelist=pricelist,
                currency=currency,
            )
            current_unit = current_pricing.recurrence_id.unit
            current_duration = product_pricing._compute_duration_vals(
                start_date, end_date)[current_unit]
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


        ratio = (
            ceil(current_duration or 0) / pricing.recurrence_id.duration
            if pricing.recurrence_id.duration
            else 1
        )
        if current_unit != pricing.recurrence_id.unit:
            ratio *= (
                PERIOD_RATIO[current_unit] / PERIOD_RATIO[pricing.recurrence_id.unit]
            )

        # Application des taxes
        product_taxes = res['product_taxes']
        if product_taxes:
            current_price = self.env['product.template']._apply_taxes_to_price(
                current_price, currency, product_taxes,
                res['taxes'], product_or_template,
            )

        # Filtrer les tarifs publiés
        all_suitable_pricings = (
            product_pricing._get_suitable_pricings(product_or_template, pricelist)
        )
        published_pricings = (
            all_suitable_pricings.filtered(lambda p: p.mb_website_published)
        )

        if not published_pricings:
            pricing_table = []
        else:
            # Garder le tarif le plus bas par recurrence
            best_pricings = {}
            for p in published_pricings:
                if best_pricings.get(p.recurrence_id, float('inf')).price > p.price:
                    best_pricings[p.recurrence_id] = p

            published_pricings = best_pricings.values()

            def _pricing_price(pricing):
                price = self.env['product.template']._apply_taxes_to_price(
                    pricing.price, currency, product_taxes,
                    res['taxes'], product_or_template
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

        if product_or_template.is_product_variant:
            product = product_or_template
            has_stock_notification = (
                product._has_stock_notification(self.env.user.partner_id)
                or request and product.id in request.session.get(
                    'product_with_stock_notification_enabled', set())
            )
            stock_notification_email = (
                request and request.session.get('stock_notification_email', '')
            )
            res.update({
                'free_qty': free_qty,
                'cart_qty': product._get_cart_qty(website),
                'uom_name': product.uom_id.name,
                'uom_rounding': product.uom_id.rounding,
                'show_availability': product_or_template.show_availability,
                'out_of_stock_message': product_or_template.out_of_stock_message,
                'has_stock_notification': has_stock_notification,
                'stock_notification_email': stock_notification_email,
            })
        else:
            res.update({
                'free_qty': 0,
                'cart_qty': 0,
            })

        _logger.info(
            "Valeur finale de free_qty pour le produit %s: %s",
            product_or_template.name, free_qty)

        return {
            **res,
            'is_rental': True,
            'rental_duration': recurrence.duration,
            'rental_duration_unit': recurrence.unit,
            'rental_unit': recurrence._get_unit_label(recurrence.duration),
            'default_start_date': default_start_date,
            'default_end_date': default_end_date,
            'current_rental_duration': ceil(current_duration or 0),
            'current_rental_unit': current_pricing.recurrence_id._get_unit_label(
                current_duration),
            'current_rental_price': current_price,
            'current_rental_price_per_unit': current_price / (ratio or 1),
            'base_unit_price': 0,
            'base_unit_name': False,
            'pricing_table': pricing_table,
            'prevent_zero_price_sale': website.prevent_zero_price_sale
            and currency.is_zero(current_price),
        }

    def calculate_min_availability_over_period(self, product_or_template,
                                               start_date, end_date):
        """
        Calcule la quantité minimale disponible sur une période donnée
        en tenant compte de toutes les sous-périodes retournées par _get_availabilities
        """
        availabilities = product_or_template._get_availabilities(
            from_date=start_date,
            to_date=end_date,
            warehouse_id=False,
            with_cart=True
        )

        if not availabilities:
            return 0

        min_qty = None

        # Parcourir toutes les périodes et trouver celles qui chevauchent
        for availability in availabilities:
            period_start = availability['start']
            period_end = availability['end']

            # Calculer la zone de chevauchement
            overlap_start = max(period_start, start_date)
            overlap_end = min(period_end, end_date)

            # S'il y a un chevauchement
            if overlap_start < overlap_end:
                quantity = int(availability.get('quantity_available', 0))

                if min_qty is None:
                    min_qty = quantity  # Premier résultat
                else:
                    min_qty = min(min_qty, quantity)

                _logger.info("Chevauchement trouvé: %s à %s, quantité: %s",
                             overlap_start, overlap_end, quantity)

        # Si aucun chevauchement trouvé
        if min_qty is None:
            _logger.warning("Aucun chevauchement trouvé entre les périodes"
                            " disponibles et %s-%s",
                            start_date, end_date)
            return 0

        return max(0, min_qty)  # S'assurer que la quantité n'est pas négative
