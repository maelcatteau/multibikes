/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import publicWidget from '@web/legacy/js/public/public_widget';
import { deserializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

const originalIsCustomDate = publicWidget.registry.WebsiteSaleDaterangePicker.prototype._isCustomDate;

patch(publicWidget.registry.WebsiteSaleDaterangePicker.prototype, {
    /**
     * Load renting constraints.
     *
     * The constraints are now based on temporal periods with specific schedules,
     * day configurations, and minimal durations per period.
     *
     * @private
     */
    async _loadRentingConstraints() {
        return rpc("/rental/product/constraints").then((constraints) => {
            this.rentingPeriods = constraints.renting_periods;
            this.websiteTz = constraints.website_tz;
            this.rentingMinimalTime = constraints.renting_minimal_time

            console.log('[WebsiteSaleDaterangePicker] Événement renting_constraints_loaded déclenché avec:', {
                rentingPeriods: this.rentingPeriods,
                websiteTz: this.websiteTz,
                rentingMinimalTime: this.rentingMinimalTime
            });

            $('.oe_website_sale').trigger('renting_constraints_changed', {
                rentingMinimalTime: this.rentingMinimalTime,
                websiteTz: this.websiteTz,
            });
            $('.oe_website_sale').trigger('renting_constraints_loaded', {
                rentingPeriods: this.rentingPeriods,
            })
        });
    },
    /**
     * Check if the date is valid (can be selected in datepicker).
     *
     * @param {DateTime} date
     * @private
     */
    _isValidDate(date) {
        if (!this.rentingPeriods || this.rentingPeriods.length === 0) {
            return false;
        }
        
        const activePeriod = this.rentingPeriods.find(period => {
            const startDate = deserializeDateTime(period.start_date);
            const endDate = deserializeDateTime(period.end_date);
            return date >= startDate && date <= endDate;
        });
        
        if (!activePeriod || activePeriod.is_closed) {
            return false;
        }
        const dayConfig = activePeriod.day_configs[date.weekday];
        const isValid = Boolean(dayConfig && dayConfig.is_open);
        
        
        
        return isValid;
    },
    
    /**
     * Get CSS classes for date cells based on stock availability and pickup/return availability.
     *
     * @param {DateTime} date
     * @private
     * @returns {Array} Array of CSS class names
     */
    _isCustomDate(date) {
        // D'abord, récupérer le comportement par défaut (gestion stock)
        const result = originalIsCustomDate.call(this, date);
        
        // Si le stock indique que la date est dangereuse (indisponible), 
        // on garde cette indication prioritaire
        if (result.includes('o_daterangepicker_danger')) {
            return result;
        }
        
        // Sinon, appliquer notre logique de pickup/return
        if (!this.rentingPeriods || this.rentingPeriods.length === 0) {
            return result;   
        }
        
        const activePeriod = this.rentingPeriods.find(period => {
            const startDate = deserializeDateTime(period.start_date);
            const endDate = deserializeDateTime(period.end_date);
            return date >= startDate && date <= endDate;
        });
        
        if (!activePeriod || activePeriod.is_closed) {
            return result;
        }
        
        const dayConfig = activePeriod.day_configs[date.weekday];
        if (!dayConfig || !dayConfig.is_open) {
            return result;
        }
        
        // Ajouter nos classes personnalisées
        const canPickup = dayConfig.pickup.allowed;
        const canReturn = dayConfig.return.allowed;
        
        if (canPickup && !canReturn) {
            result.push('rental-pickup-only');
        } else if (!canPickup && canReturn) {
            result.push('rental-return-only'); 
        }
        
        return result;
    },
});