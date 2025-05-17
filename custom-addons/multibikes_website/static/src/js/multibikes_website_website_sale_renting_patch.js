/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { patch } from '@web/core/utils/patch';
import { sprintf } from '@web/core/utils/strings';
import { _t } from '@web/core/l10n/translation';
import { msecPerUnit, unitMessages } from '@website_sale_renting/js/renting_mixin';

const { DateTime } = luxon;

console.log('[multibikes_website] Script loaded');
console.log('[multibikes_website] WebsiteSale available:', !!publicWidget.registry.WebsiteSale);
console.log('[multibikes_website] WebsiteSaleDaterangePicker available:', !!publicWidget.registry.WebsiteSaleDaterangePicker);

// Patcher le prototype de WebsiteSale pour affecter toutes les instances
patch(publicWidget.registry.WebsiteSale.prototype, {
    _getInvalidMessage(startDate, endDate, productId = false) {
        console.log('[multibikes_website] override _getInvalidMessage in WebsiteSale');
        let message;
        if (!this.rentingUnavailabilityDays || !this.rentingMinimalTime) {
            return;
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
                } else if (startDate.startOf("day") < DateTime.now().setZone(this.websiteTz).startOf("day")) {
                    message = _t("The pickup date cannot be in the past.");
                } else {
                    const { unit, duration: minimalDuration, start_date: minStart, end_date: minEnd } = this.rentingMinimalTime;
                    if (["hour", "day", "week", "month"].includes(unit)) {
                        const durationInUnits = rentingDuration / msecPerUnit[unit];
                        if (durationInUnits < minimalDuration) {
                            const formatted = sprintf(unitMessages[unit], minimalDuration);
                            if (minStart && minEnd) {
                                message = _t(
                                    "The rental duration is too short. The minimum rental period is %s between %s and %s.",
                                    formatted, minStart, minEnd
                                );
                            } else {
                                message = _t(
                                    "The rental duration is too short. The minimum rental period is %s.",
                                    formatted
                                );
                            }
                        }
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }
        console.log('[multibikes_website] Validation message in WebsiteSale:', message || 'OK');
        return message;
    },
});

// Patcher le prototype de WebsiteSaleDaterangePicker pour affecter toutes ses instances
if (publicWidget.registry.WebsiteSaleDaterangePicker) {
    patch(publicWidget.registry.WebsiteSaleDaterangePicker.prototype, {
        _getInvalidMessage(startDate, endDate, productId = false) {
            console.log('[multibikes_website] override _getInvalidMessage in WebsiteSaleDaterangePicker');
            let message;
            // ... (même logique que ci-dessus)
            if (!this.rentingUnavailabilityDays || !this.rentingMinimalTime) {
                return;
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
                    } else if (startDate.startOf("day") < DateTime.now().setZone(this.websiteTz).startOf("day")) {
                        message = _t("The pickup date cannot be in the past.");
                    } else {
                        const { unit, duration: minimalDuration, start_date: minStart, end_date: minEnd } = this.rentingMinimalTime;
                        if (["hour", "day", "week", "month"].includes(unit)) {
                            const durationInUnits = rentingDuration / msecPerUnit[unit];
                            if (durationInUnits < minimalDuration) {
                                const formatted = sprintf(unitMessages[unit], minimalDuration);
                                if (minStart && minEnd) {
                                    message = _t(
                                        "The rental duration is too short. The minimum rental period is %s between %s and %s.",
                                        formatted, minStart, minEnd
                                    );
                                } else {
                                    message = _t(
                                        "The rental duration is too short. The minimum rental period is %s.",
                                        formatted
                                    );
                                }
                            }
                        }
                    }
                }
            } else {
                message = _t("Please select a rental period.");
            }
            console.log('[multibikes_website] Validation message in WebsiteSaleDaterangePicker:', message || 'OK');
            return message;
        },
    });
    console.log('[multibikes_website] Patch applied to WebsiteSaleDaterangePicker prototype');
}
