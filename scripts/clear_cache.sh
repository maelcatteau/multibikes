#!/bin/bash
echo "🔥 NUCLEAR REFRESH pour multibikes_website"

ADDON_PATH="./custom-addons/multibikes_website"

# 1. Force un changement dans les JS pour bypasser le cache
echo "💥 Injection timestamp dans les JS..."
sed -i "1i/* FORCE REFRESH: $(date '+%Y-%m-%d %H:%M:%S') */" \
  "$ADDON_PATH/static/src/js/multibikes_website_sale.js" \
  "$ADDON_PATH/static/src/js/multibikes_website_sale_DaterangePicker.js"

# 2. Destruction totale du cache Odoo
echo "☢️ Destruction cache Odoo..."
docker compose exec -T odoo-dev python3 /usr/bin/odoo shell -d 'multibikes-test' <<'EOF'
# Clear TOUT ce qui touche aux assets
env['ir.attachment'].search([('url', 'ilike', '/web/assets/')]).unlink()
env['ir.attachment'].search([('name', 'ilike', '%assets%')]).unlink()
env['ir.attachment'].search([('name', 'ilike', '%multibikes_website%')]).unlink()
env['ir.qweb'].clear_caches()
env['ir.ui.view'].clear_caches()
env.registry.clear_cache()
cr.commit()
print("💀 ASSETS DÉTRUITS")
EOF

# 3. Destruction BDD niveau assets
echo "🗃️ Clear assets en BDD..."
docker compose exec -T db-dev psql -U odoo -d multibikes-test <<'EOF'
DELETE FROM ir_attachment WHERE url LIKE '/web/assets/%';
DELETE FROM ir_attachment WHERE name LIKE '%multibikes_website%';
DELETE FROM ir_attachment WHERE name LIKE '%assets%';
VACUUM ANALYZE ir_attachment;
EOF

# 4. Restart brutal
echo "🔄 Restart BRUTAL..."
docker compose restart odoo-dev
sleep 8

# 5. Force le rechargement des assets
echo "🚀 Force reload assets..."
until curl -s "http://dev.mcommemedoc.fr/web/database/selector" > /dev/null; do
    sleep 2
done

# 6. URL directe avec tous les flags anti-cache
FINAL_URL="http://dev.mcommemedoc.fr/web/login?db=multibikes-test&login=mael.catteau@gmail.com&key=admin&debug=Superngner//(2025)&force_assets_refresh=1&nocache=$(date +%s)&t=$(date +%s)"

echo ""
echo "🎯 COPY-PASTE ÇA DIRECT :"
echo "$FINAL_URL"
echo ""
echo "✅ Si ça marche pas, on passe au plan B..."
