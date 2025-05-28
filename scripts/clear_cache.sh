#!/bin/bash
echo "🧹 Nettoyage cache assets Odoo 18..."

# Clear via shell Odoo 18
docker compose exec odoo-dev python3 /usr/bin/odoo shell -d test <<EOF
# Odoo 18 : Clear des assets et bundles
env['ir.attachment'].search([
    ('name', 'ilike', 'web.assets_%')
]).unlink()

# Clear des assets compilés spécifiques à Odoo 18
env['ir.attachment'].search([
    '|', ('url', 'ilike', '/web/assets/'),
         ('res_model', '=', 'ir.ui.view')
]).unlink()

# Clear cache registry Odoo 18
env.registry.clear_cache()
env['ir.ui.view'].clear_caches()

# Nouveau dans Odoo 18 : clear des bundles JS/CSS
try:
    env['ir.qweb']._compile_directives_cache.clear()
except:
    pass

env.cr.commit()
print("✅ Cache Odoo 18 vidé")
exit()
EOF

echo "🔄 Redémarrage conteneur..."
docker compose restart odoo-dev

echo "✅ Terminé ! Accédez avec ?debug=1"
