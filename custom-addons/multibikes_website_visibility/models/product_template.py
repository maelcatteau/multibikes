# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import format_amount
from math import ceil
from odoo.http import request

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """
        Surcharge de la méthode pour filtrer les tarifs affichés dans la pricing_table
        en fonction du champ mb_website_published
        """
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not product_or_template.rent_ok:
            return res

        # La logique reste identique à la fonction d'origine
        currency = website.currency_id
        pricelist = website.pricelist_id
        ProductPricing = self.env['product.pricing']

        # Obtenir tous les tarifs disponibles (sans filtrer par mb_website_published)
        pricing = ProductPricing._get_first_suitable_pricing(product_or_template, pricelist)
        if not pricing:
            return res

        # Compute best pricing rule or set default
        order = website.sale_get_order() if website and request else self.env['sale.order']
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
            current_duration = ProductPricing._compute_duration_vals(
                start_date, end_date
            )[current_unit]
        else:
            current_unit = pricing.recurrence_id.unit
            current_duration = pricing.recurrence_id.duration
            current_pricing = pricing

        # Compute current price (sans filtrer)
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

        # apply taxes
        product_taxes = res['product_taxes']
        if product_taxes:
            current_price = self.env['product.template']._apply_taxes_to_price(
                current_price, currency, product_taxes, res['taxes'], product_or_template,
            )

        # Obtenir tous les tarifs candidats
        all_suitable_pricings = ProductPricing._get_suitable_pricings(product_or_template, pricelist)
        
        # Filtrer pour la pricing_table uniquement
        published_pricings = all_suitable_pricings.filtered(lambda p: p.mb_website_published)

        # Si aucun tarif n'est publié, ne pas afficher de tableau de prix
        if not published_pricings:
            pricing_table = []
        else:
            # If there are multiple pricings with the same recurrence, we only keep the cheapest ones
            best_pricings = {}
            for p in published_pricings:
                if p.recurrence_id not in best_pricings:
                    best_pricings[p.recurrence_id] = p
                elif best_pricings[p.recurrence_id].price > p.price:
                    best_pricings[p.recurrence_id] = p

            published_pricings = best_pricings.values()
            def _pricing_price(pricing):
                if product_taxes:
                    price = self.env['product.template']._apply_taxes_to_price(
                        pricing.price, currency, product_taxes, res['taxes'], product_or_template
                    )
                else:
                    price = pricing.price
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
            'prevent_zero_price_sale': website.prevent_zero_price_sale and currency.is_zero(
                current_price,
            ),
        }