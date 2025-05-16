/** @odoo-module **/

import { RentingMixin } from '@website_sale_renting/js/renting_mixin';
import { sprintf } from "@web/core/utils/strings";
import { _t } from "@web/core/l10n/translation";

// Surcharge du RentingMixin pour personnaliser le message d'erreur lié à la durée minimale
Object.assign(RentingMixin, {
    /**
     * Initialisation du mixin pour écouter les changements de contraintes via un événement DOM.
     */
    init: function () {
        this._super.apply(this, arguments);
        // Écouter l'événement DOM pour les changements de contraintes
        $('.oe_website_sale').on('renting_constraints_changed', this._onRentingConstraintsChanged.bind(this));
    },

    /**
     * Gestionnaire d'événement pour mettre à jour les contraintes de location lorsqu'elles changent.
     *
     * @param {Event} event
     * @param {Object} constraints
     * @private
     */
    _onRentingConstraintsChanged: function (event, constraints) {
        if (constraints.rentingUnavailabilityDays) {
            this.rentingUnavailabilityDays = constraints.rentingUnavailabilityDays;
        }
        if (constraints.rentingMinimalTime) {
            this.rentingMinimalTime = constraints.rentingMinimalTime;
        }
        if (constraints.websiteTz) {
            this.websiteTz = constraints.websiteTz;
        }
    },

    /**
     * Surcharge de _getInvalidMessage pour personnaliser le message d'erreur
     * en fonction de la durée minimale renvoyée par le backend.
     *
     * @param {DateTime} startDate
     * @param {DateTime} endDate
     * @param {number} productId
     * @returns {string} Message d'erreur personnalisé
     * @private
     */
    _getInvalidMessage: function (startDate, endDate, productId = false) {
        let message;
        if (!this.rentingUnavailabilityDays || !this.rentingMinimalTime) {
            return message;
        }
        if (startDate && endDate) {
            if (this.rentingUnavailabilityDays[startDate.weekday]) {
                message = _t("You cannot pick up your rental on that day of the week.");
            } else if (this.rentingUnavailabilityDays[endDate.weekday]) {
                message = _t("You cannot return your rental on that day of the week.");
            } else {
                const rentingDuration = endDate - startDate;
                if (rentingDuration < 0) {
                    message = _t("The return date should be after the pickup date.");
                } else if (startDate.startOf("day") < luxon.DateTime.now().setZone(this.websiteTz).startOf("day")) {
                    message = _t("The pickup date cannot be in the past.");
                } else if (
                    ["hour", "day", "week", "month"].includes(this.rentingMinimalTime.unit)
                ) {
                    const unit = this.rentingMinimalTime.unit;
                    const minimalDuration = this.rentingMinimalTime.duration;
                    const msecPerUnit = {
                        hour: 3600 * 1000,
                        day: 3600 * 1000 * 24,
                        week: 3600 * 1000 * 24 * 7,
                        month: 3600 * 1000 * 24 * 30,
                    };
                    const unitMessages = {
                        hour: _t("(%s hours)."),
                        day: _t("(%s days)."),
                        week: _t("(%s weeks)."),
                        month: _t("(%s months)."),
                    };
                    if (rentingDuration / msecPerUnit[unit] < minimalDuration) {
                        message = _t(
                            "The rental duration is too short. The minimum rental period is %s",
                            sprintf(unitMessages[unit], minimalDuration)
                        );
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }
        return message;
    }
});
