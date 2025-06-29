#!/usr/bin/env nu

# Dictionnaire global des containers
export const CONTAINERS = {
    dev: {
        odoo: "odoo-dev",
        db: "odoo-deployment-db-dev-1"
    },
    staging: {
        odoo: "odoo-staging",
        db: "odoo-deployment-db-staging-1"
    },
    prod: {
        odoo: "odoo-prod",
        db: "odoo-deployment-db-prod-1"
    }
}