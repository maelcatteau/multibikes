/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';
import { _t } from "@web/core/l10n/translation";
const { DateTime } = luxon; // S'assurer que Luxon est disponible

WebsiteSale.include({
    events: Object.assign(WebsiteSale.prototype.events || {}, {
        'renting_constraints_loaded': '_onRentingPeriodsLoaded',
    }),

    /**
     * Initialisation pour s'assurer que les propriétés existent.
     */
    init() {
        this._super.apply(this, arguments);
        this.rentingPeriods = null;
        this.websiteTz = 'UTC';
        this.dailyConfigs = {}; // Configuration horaire de la période active
        this.activeRentingPeriod = null; // Pour stocker la période actuellement appliquée
    },

    /**
     * Surcharge de onChangeCombination.
     */
    _onChangeCombination: async function (ev, $parent, combination) {
        // Laisser Odoo gérer ses appels RPC et mettre à jour les infos de base du produit/variante
        const result = await this._super.apply(this, arguments);

        // Mettre à jour les contraintes en fonction de la période de location.
        // Ceci va lire la date sélectionnée, trouver la période, mettre à jour this.*, et déclencher la re-validation.
        this._updateRentalConstraints($parent);

        return result;
    },

    /**
     * Met à jour this.rentingPeriods et this.websiteTz depuis l'événement.
     */
    _onRentingPeriodsLoaded(_event, info) {
        this.rentingPeriods = info.rentingPeriods;
    },

    /**
     * Surcharge pour gérer les contraintes.
     */
    _onRentingConstraintsChanged(_event, info) {
        // console.log("[WebsiteSale] _onRentingConstraintsChanged CALLED with info:", info);

        // Propriétés générales du produit
        if (info.rentingAvailabilities) {
            this.rentingAvailabilities = info.rentingAvailabilities;
        }
        if (info.preparationTime !== undefined) {
            this.preparationTime = info.preparationTime;
        }

        // Si l'événement est déclenché par notre _updateRentalConstraints, les valeurs
        // this.rentingUnavailabilityDays, this.rentingMinimalTime, this.dailyConfigs
        // sont DÉJÀ À JOUR avec les infos de la PÉRIODE.
        // L'événement sert à dire à Odoo de REVALIDER.

        // Important: NE PAS appeler this._super() ici pour un contrôle total.
        // Le framework de location d'Odoo écoute cet événement et va lancer la re-validation
        // de la date/heure, ce qui appellera _getInvalidMessage.
    },

    /**
     * Génère un objet des jours d'indisponibilité à partir de la configuration des jours.
     * @param {Object} dayConfigs Exemple: { "1": {is_open: true, pickup:{allowed:true}, return:{allowed:true}}, ...}
     * @returns {Object} {1: false, 2: true, ...} (Luxon weekday: 1=lundi, true=indisponible)
     */
    _generateUnavailabilityDays: function(dayConfigs) {
        const unavailabilityDays = {};
        if (!dayConfigs || Object.keys(dayConfigs).length === 0) {
            // Si pas de config spécifique, on peut considérer tous les jours comme potentiellement indisponibles

            for (let day = 1; day <= 7; day++) {
                unavailabilityDays[day] = true; // Par défaut, indisponible.
            }
            return unavailabilityDays; 
        }

        for (let day = 1; day <= 7; day++) { // Luxon: 1 (Lundi) à 7 (Dimanche)
            const dayKey = day.toString();
            const config = dayConfigs[dayKey];

            // Un jour est globalement indisponible si :
            // 1. Il n'a pas de config OU (sauf si on veut que ce soit "ouvert par défaut")
            // 2. Il est marqué 'is_open: false' OU
            // 3. Ni pickup ni return ne sont autorisés pour ce jour.
            const isUnavailable = !config ||
                                !config.is_open ||
                                (!config.pickup?.allowed && !config.return?.allowed);
            unavailabilityDays[day] = isUnavailable;
        }
        console.log('[WebsiteSale] Jours d\'indisponibilité générés à partir de dailyConfigs (generateuna):', unavailabilityDays);
        return unavailabilityDays;
    },

    /**
     * Méthode pour mettre à jour les contraintes de locations en 
     * fonction de la date de début de la location. En déclenchant
     * un événement renting_constraints_changed sur le document.
     *
     * @private
     * @param {JQueryElement} $parent - Élément parent du formulaire
     * @returns {Promise} Promesse de mise à jour des contraintes
     */
    _updateRentalConstraints: async function ($parent) {
        console.log('[WebsiteSale] _updateRentalConstraints appelé');
        
        // Obtenir la date de début de location
        const rentingDates = this._getRentingDates();
        const startDate = rentingDates.start_date;
        const productId = this._getProductId($parent?.closest('form'));
        
        console.log('[WebsiteSale] Données initiales:', { 
            startDate: startDate || 'non défini',
            productId: productId || 'non défini'
        });
        
        if (!this.rentingPeriods) {
            console.warn("[WebsiteSale] Impossible de mettre à jour les contraintes : données non chargées");
            return;
        }

        // Si pas de date de début, utiliser la date actuelle
        let dateToCheck;
        if (!startDate) {
            dateToCheck = new Date();
        } else if (typeof startDate === 'string') {
            dateToCheck = new Date(startDate);
        } else if (startDate instanceof Date) {
            dateToCheck = startDate;
        } else if (startDate.isLuxonDateTime) {
            // Cas d'un objet DateTime Luxon
            dateToCheck = startDate.toJSDate();
        } else {
            dateToCheck = new Date(startDate);
        }
        
        console.log('[WebsiteSale] Date à vérifier:', dateToCheck);
        
        // Formater la date en YYYY-MM-DD pour la comparaison avec les périodes
        const formattedDate = dateToCheck.toISOString().split('T')[0];
        console.log('[WebsiteSale] Date formatée pour comparaison:', formattedDate);
        
        // Trouver la période correspondant à la date
        const matchingPeriod = this.rentingPeriods.find(period => {
            return period.start_date <= formattedDate && period.end_date >= formattedDate;
        });
        
        console.log('[WebsiteSale] Période correspondante:', matchingPeriod);
        
        if (!matchingPeriod) {
            console.warn(`[WebsiteSale] Aucune période trouvée pour la date ${formattedDate}`);
            // Utiliser les contraintes par défaut si aucune période ne correspond
            return;
        }
        
        // Obtenir le jour de la semaine (0-6, dimanche = 0 en JavaScript)
        const dayOfWeek = dateToCheck.getDay();
        // Ajuster pour avoir lundi = 0, dimanche = 6 (format Odoo)
        const odooDoW = (dayOfWeek + 6) % 7;
        
        console.log('[WebsiteSale] Jour de la semaine (format Odoo):', odooDoW);
        
        // Obtenir la configuration du jour pour cette période
        const dayConfig = matchingPeriod.day_configs[odooDoW];
        
        console.log('[WebsiteSale] Configuration du jour:', dayConfig);

        const rentingUnavailabilityDays = this._generateUnavailabilityDays(matchingPeriod.day_configs);
        
        const eventData = {
            rentingUnavailabilityDays: rentingUnavailabilityDays,
            rentingMinimalTime: {
                duration: matchingPeriod.minimal_time_duration,
                unit: matchingPeriod.minimal_time_unit,
                name: matchingPeriod.minimal_time_name,
                start_date: matchingPeriod.start_date,
                end_date: matchingPeriod.end_date
            },
            websiteTz: this.websiteTz,
            dailyConfigs: matchingPeriod.day_configs
        };
        
        console.log('[WebsiteSale] Déclenchement événement renting_constraints_changed avec:', eventData);
        
        // Déclencher l'événement DOM
        $('.oe_website_sale').trigger('renting_constraints_changed', eventData);

        return;
    },

    /**
     * Compare la durée de location actuelle avec la durée minimale requise.
     */
    _compareRentalDurations(actualRental, minimalRentalRequirement) {
        if (!actualRental || typeof actualRental.duration !== 'number' || !actualRental.unit ||
            !minimalRentalRequirement || typeof minimalRentalRequirement.duration !== 'number' || !minimalRentalRequirement.unit) {
            console.warn("[WebsiteSale] Comparaison de durée impossible: données invalides", actualRental, minimalRentalRequirement);
            return true;
        }

        const unitToHours = {
            'hour': 1, 'hours': 1,
            'day': 24, 'days': 24,
            'week': 24 * 7, 'weeks': 24 * 7,
        };

        const actualDurationInHours = actualRental.duration * (unitToHours[actualRental.unit.toLowerCase()] || 0);
        const minimalDurationInHours = minimalRentalRequirement.duration * (unitToHours[minimalRentalRequirement.unit.toLowerCase()] || 0);

        if (actualDurationInHours === 0 && minimalDurationInHours > 0) return false; // Si actuel est 0 et min > 0
        if (minimalDurationInHours === 0 ) return true; // Si min est 0, toujours valide

        return actualDurationInHours >= minimalDurationInHours;
    },

    /**
     * Vérifie si l'heure donnée est valide selon this.dailyConfigs.
     */
    _isValidTime: function (dateTimeToCheck, type = 'pickup') {
        if (!dateTimeToCheck || !dateTimeToCheck.isValid) return false;
        if (!this.dailyConfigs || Object.keys(this.dailyConfigs).length === 0) {
            console.warn("[WebsiteSale] _isValidTime: dailyConfigs manquant. Par défaut, validation horaire permissive.");
            return true; // Ou false si vous voulez bloquer par défaut
        }

        const dayOfWeek = dateTimeToCheck.weekday; // Luxon: 1 (Lundi) à 7 (Dimanche)
        const dayConfig = this.dailyConfigs[dayOfWeek.toString()];

        if (!dayConfig || !dayConfig.is_open) return false;

        const slotConfig = dayConfig[type]; // ex: dayConfig.pickup
        if (!slotConfig || !slotConfig.allowed) return false;

        // SI vous avez des plages horaires détaillées dans slotConfig (ex: slotConfig.time_slots)
        // if (slotConfig.time_slots && slotConfig.time_slots.length > 0) {
        //     const currentTimeInMinutes = dateTimeToCheck.hour * 60 + dateTimeToCheck.minute;
        //     for (const slot of slotConfig.time_slots) { // ex: slot = { start_time: "08:00", end_time: "12:00" }
        //         const slotStartMinutes = parseInt(slot.start_time.split(':')[0]) * 60 + parseInt(slot.start_time.split(':')[1]);
        //         const slotEndMinutes = parseInt(slot.end_time.split(':')[0]) * 60 + parseInt(slot.end_time.split(':')[1]);
        //         // Attention: la fin de la plage est souvent exclusive (ex: jusqu'à 11:59 si end_time est 12:00)
        //         if (currentTimeInMinutes >= slotStartMinutes && currentTimeInMinutes < slotEndMinutes) {
        //             return true;
        //         }
        //     }
        //     return false; // Aucune plage ne correspond
        // }

        // Sinon, exemple simple si dayConfig contient directement des heures min/max
        // Par exemple : if (dateTimeToCheck.hour < slotConfig.minHour || dateTimeToCheck.hour > slotConfig.maxHour) return false;

        // Pour l'instant, si on arrive ici et que `allowed` est true, on considère ça comme valide au niveau horaire basique.
        // Votre message original avait une logique 8h-18h, 00/30 min, vous devrez la réintroduire ici
        // si this.dailyConfigs ne contient pas cette granularité.
        const hour = dateTimeToCheck.hour;
        const minute = dateTimeToCheck.minute;
        if (hour < 8 || hour >= 18) { // De _08_:00 à _17_:59
            return false;
        }
        if (minute !== 0 && minute !== 30) {
            return false;
        }

        return true;
    },

    /**
     * Récupère le message d'erreur de validation pour les dates de location.
     * C'EST CETTE FONCTION QUI EST APPELÉE PAR ODOO POUR LA VALIDATION.
     * Elle doit utiliser les `this.rentingUnavailabilityDays`, `this.rentingMinimalTime` et `this.dailyConfigs`
     * qui ont été mis à jour par `_updateRentalConstraints`.
     */
    _getInvalidMessage: function ($displayContainer, startDate, endDate) {
        // Note: La méthode parente de _getInvalidMessage peut déjà faire certaines validations.
        // On peut l'appeler ou la réimplémenter complètement.
        // Pour l'instant, réimplémentons avec votre logique spécifique.

        console.log("[WebsiteSale] _getInvalidMessage appelé avec:", {
            startDate: startDate,
            endDate: endDate,
            rentingUnavailabilityDays: this.rentingUnavailabilityDays,
            rentingMinimalTime: this.rentingMinimalTime,
            dailyConfigs: this.dailyConfigs,
        });

        let message = "";

        if (startDate && endDate) {
            // 1. VALIDATION JOURS DE LA SEMAINE (basé sur this.rentingUnavailabilityDays mis à jour)
            // this.rentingUnavailabilityDays devrait être {1: true/false, 2: true/false, ...} où true = non disponible
            if (this.rentingUnavailabilityDays && this.rentingUnavailabilityDays[startDate.weekday]) {
                message = _t("You cannot pick up your rental on that day of the week.");
            } else if (this.rentingUnavailabilityDays && this.rentingUnavailabilityDays[endDate.weekday]) {
                message = _t("You cannot return your rental on that day of the week.");
            }
            // 2. VALIDATION HORAIRE (basé sur this.dailyConfigs, via _isValidTime)
            else if (!this._isValidTime(startDate, 'pickup')) {
                message = _t("The pickup time is outside allowed hours.");
            } else if (!this._isValidTime(endDate, 'return')) {
                message = _t("The return time is outside allowed hours.");
            }
            // 3. AUTRES VALIDATIONS DE DATE
            else {
                const rentingDuration = endDate.diff(startDate); // Luxon Duration object
                if (rentingDuration.as('milliseconds') < 0) {
                    message = _t("The return date should be after the pickup date.");
                } else if (startDate.startOf("day") < DateTime.now().setZone(this.websiteTz).startOf("day")) {
                    message = _t("The pickup date cannot be in the past.");
                } else {
                    // 4. VALIDATION DE DURÉE (basé sur this.rentingMinimalTime mis à jour)
                    const minimalReq = this.rentingMinimalTime; // Ex: { duration: 2, unit: 'days', name: "2 Days" }

                    if (minimalReq && typeof minimalReq.duration === 'number' && minimalReq.unit) {
                        // Convertir la durée réelle en unité comparable à minimalReq ou vice-versa
                        // Pour simplifier, on utilise _compareRentalDurations.
                        // On a besoin de la durée de location actuelle tirée de startDate et endDate
                        // ou des infos de la variante de prix SI elle spécifie une durée fixe.

                        // La logique originale utilisait combinationInfo.rental_duration.
                        // Ceci est pertinent si le prix est pour une durée FIXE (Week-end, Semaine).
                        // Si la durée est flexible (prix par jour/heure), on compare la durée sélectionnée.

                        const combinationInfo = this.productPricelistItem?.combinationInfo;
                        let actualRentalIsFixedDuration = false;
                        let actualRentalDurationForComparison = { // Par défaut, la durée sélectionnée
                            duration: endDate.diff(startDate, minimalReq.unit /* ou 'hours', 'days' etc. */).as(minimalReq.unit),
                            unit: minimalReq.unit
                        };

                        if (combinationInfo && typeof combinationInfo.rental_duration === 'number' && combinationInfo.rental_duration_unit) {
                            // Le prix est pour une durée fixe, comparons cette durée.
                            actualRentalDurationForComparison = {
                                duration: combinationInfo.rental_duration,
                                unit: combinationInfo.rental_duration_unit,
                            };
                            actualRentalIsFixedDuration = true;
                            // console.log("[WebsiteSale] _getInvalidMessage: Utilisation de la durée fixe de la variante de prix pour la comparaison:", actualRentalDurationForComparison);
                        } else {
                            // Convertir la durée sélectionnée (endDate - startDate) dans l'unité de minimalReq.
                            // Exemple : si minimalReq.unit est 'days', convertir rentingDuration en jours.
                            // Pour que ce soit flexible, on peut utiliser _compareRentalDurations qui convertit en heures.
                            const durationUnits = ['hours', 'days', 'weeks']; // Unités pour .as()
                            let selectedDurationValue;
                            let selectedUnit;

                            for (const unit of durationUnits) { // Trouver la plus grande unité où la durée est >= 1
                                const val = rentingDuration.as(unit);
                                if (val >= 1) {
                                    selectedDurationValue = Math.floor(val); // ou garder les décimales selon la précision voulue
                                    selectedUnit = unit;
                                    // break; // On pourrait s'arrêter à la première unité pertinente
                                }
                            }
                            if (!selectedUnit && rentingDuration.as('milliseconds') > 0) { // Si durée < 1 heure mais > 0ms
                                selectedDurationValue = rentingDuration.as('hours');
                                selectedUnit = 'hours';
                            }

                            if (selectedDurationValue !== undefined && selectedUnit) {
                                actualRentalDurationForComparison = {
                                    duration: selectedDurationValue,
                                    unit: selectedUnit
                                };
                            } else if (rentingDuration.as('milliseconds') === 0 && minimalReq.duration > 0) {
                                // Si durée sélectionnée est nulle mais une durée min est exigée
                                actualRentalDurationForComparison = { duration: 0, unit: minimalReq.unit};
                            }
                            // console.log("[WebsiteSale] _getInvalidMessage: Utilisation de la durée sélectionnée pour la comparaison:", actualRentalDurationForComparison);
                        }


                        if (!this._compareRentalDurations(actualRentalDurationForComparison, minimalReq)) {
                            let formattedMinimalDuration = minimalReq.name || `${minimalReq.duration} ${minimalReq.unit}(s)`;
                            if (actualRentalIsFixedDuration) {
                                message = _t("The selected product variant has a rental duration of %s, but the period requires a minimum of %s.",
                                    `${actualRentalDurationForComparison.duration} ${actualRentalDurationForComparison.unit}`,
                                    formattedMinimalDuration
                                );
                            } else {
                                message = _t("The rental duration is too short. The minimum for this period is %s.", formattedMinimalDuration);
                            }
                        }
                    }
                }
            }
        } else {
            message = _t("Please select a rental period.");
        }
        // La valeur de retour de _getInvalidMessage dans Odoo est généralement le message lui-même ou undefined/null
        return message || this._super.apply(this, arguments); // Pourrait appeler super au cas où mais notre logique doit primer.
                                                               // Ou simplement `return message;` si on gère tout.
    },
});
