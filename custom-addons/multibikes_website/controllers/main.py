# -*- coding: utf-8 -*-

from odoo import http, fields
from odoo.http import request
from odoo.addons.website_sale_renting.controllers.main import WebsiteSaleRenting
from datetime import timedelta

class WebsiteSaleRentingCustom(WebsiteSaleRenting):
    
    @http.route('/rental/product/constraints', type='json', auth="public", methods=['POST'], website=True)
    def renting_product_constraints(self):
        """Return rental product constraints from periods configuration.

        Constraints include:
        - Temporal periods with specific schedules and durations
        - Day configurations for pickup/return per period
        - Website timezone

        :rtype: dict
        """
        periods_data = self._get_rental_periods()
        
        return {
            'renting_periods': periods_data,
            'website_tz': request.website.tz,
            'renting_minimal_time': {
                'duration': '1',
                'unit': 'hour'
            },
        }
    
    def _get_rental_periods(self):
        """Get rental periods data for the next 3 years.
        
        :rtype: list
        """
        today = fields.Date.today()
        end_date = today + timedelta(days=3*365)
        
        periods = request.env['mb.renting.period'].search([
            ('company_id', '=', request.env.company.id),
            ('end_date', '>=', today),
            ('start_date', '<=', end_date)
        ])
        
        periods_data = []
        for period in periods:
            day_configs = self._format_day_configs(period.day_configs)
            
            periods_data.append({
                'id': period.id,
                'name': period.name,
                'start_date': fields.Datetime.to_string(period.start_date),
                'end_date': fields.Datetime.to_string(period.end_date),
                'is_closed': period.is_closed,
                'minimal_time': {
                    'duration': period.recurrence_duration,
                    'unit': period.recurrence_unit,
                    'name': period.recurrence_name,
                },
                'day_configs': day_configs
            })
        
        return periods_data
    
    def _format_day_configs(self, day_configs):
        """Format day configurations data.
        
        :param day_configs: recordset of mb.renting.day.config
        :rtype: dict
        """
        configs = {}
        for config in day_configs:
            configs[config.day_of_week] = {
                'is_open': config.is_open,
                'pickup': {
                    'allowed': config.allow_pickup,
                    'hour_from': config.pickup_hour_from,
                    'hour_to': config.pickup_hour_to,
                },
                'return': {
                    'allowed': config.allow_return,
                    'hour_from': config.return_hour_from,
                    'hour_to': config.return_hour_to,
                }
            }
        return configs
