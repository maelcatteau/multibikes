#!/usr/bin/env nu

use config.nu CONTAINERS

# Backup via API Odoo
export def backup [environment: string, --output (-o): string] {
    # Configuration par environnement
    let config = {
        dev: {
            url: "https://dev.multibikes.fr"
        },
        staging: {
            url: "https://staging.multibikes.fr"
        },
        prod: {
            url: "https://odoo.multibikes.fr"
        }
    }

    let env_config = ($config | get $environment)
    let timestamp = (date now | format date "%Y%m%d_%H%M%S")
    let filename = if $output != null {
        $output
    } else {
        $"backup_($environment)_($timestamp).zip"
    }

    print $"💾 Starting backup from ($environment)..."
    print $"🌐 URL: ($env_config.url)"

    # Demander le nom de la base de données
    print "🗃️ Please enter database name:"
    let db_name = (input)

    # Demander le mot de passe master
    print "🔐 Please enter Odoo master password:"
    let master_password = (input --suppress-output)

    # URL de l'API backup
    let backup_url = $"($env_config.url)/web/database/backup"

    print $"⏳ Creating backup..."

    # Appel API avec les données de formulaire
    try {
        let form_data = {
            master_pwd: $master_password,
            name: $db_name,
            backup_format: "zip"
        }

        http post $backup_url $form_data --content-type "application/x-www-form-urlencoded" | save $filename

        print $"✅ Backup completed: ($filename)"

        # Afficher la taille du fichier
        let file_size = (ls $filename | get size | first)
        print $"📦 File size: ($file_size)"

    } catch { |e|
        print $"❌ Backup failed: ($e.msg)"
        print "💡 Check master password and database name"
    }
}

# Restore via API Odoo
export def restore [
    target_environment: string,
    --from-env (-e): string,          # Restaurer depuis un autre environnement
    --from-file (-f): string,         # Restaurer depuis un fichier local
    --new-name (-n): string           # Nouveau nom de DB (optionnel)
] {
    # Configuration par environnement
    let config = {
        dev: {
            url: "https://dev.multibikes.fr"
        },
        staging: {
            url: "https://staging.multibikes.fr"
        },
        prod: {
            url: "https://odoo.multibikes.fr"
        }
    }

    let target_config = ($config | get $target_environment)

    # Vérifier les options
    if ($from_env == null and $from_file == null) {
        print "❌ You must specify either --from-env or --from-file"
        return
    }

    if ($from_env != null and $from_file != null) {
        print "❌ Please use only one option: --from-env OR --from-file"
        return
    }

    print $"🔄 Starting restore to ($target_environment)..."
    print $"🌐 Target URL: ($target_config.url)"

    let backup_file = if $from_env != null {
        # Backup depuis un autre environnement
        let source_config = ($config | get $from_env)
        print $"📥 Creating backup from ($from_env)..."

        print $"🔐 Please enter master password for SOURCE ($from_env):"
        let source_master_password = (input --suppress-output)

        print "🗃️ Please enter source database name:"
        let source_db = (input)

        let timestamp = (date now | format date "%Y%m%d_%H%M%S")
        let temp_backup = $"temp_backup_($timestamp).zip"

        # Créer le backup temporaire
        let backup_url = $"($source_config.url)/web/database/backup"
        let form_data = {
            master_pwd: $source_master_password,
            name: $source_db,
            backup_format: "zip"
        }

        try {
            http post $backup_url $form_data --content-type "application/x-www-form-urlencoded" | save $temp_backup
            print $"✅ Temporary backup created: ($temp_backup)"
            $temp_backup
        } catch { |e|
            print $"❌ Backup failed: ($e.msg)"
            return
        }
    } else {
        # Utiliser fichier existant
        if not ($from_file | path exists) {
            print $"❌ File not found: ($from_file)"
            return
        }
        $from_file
    }

    # Demander le mot de passe master pour la cible
    print $"🔐 Please enter master password for TARGET ($target_environment):"
    let target_master_password = (input --suppress-output)

    # Demander le nom de la DB de destination
    let target_db = if $new_name != null {
        $new_name
    } else {
        print "🗃️ Please enter target database name:"
        input
    }

    print $"⏳ Restoring to database ($target_db)..."

    # URL de l'API restore
    let restore_url = $"($target_config.url)/web/database/restore"

    try {
        # Utiliser curl pour le multipart/form-data (plus fiable pour les fichiers)
        let curl_result = (
            ^curl -X POST $restore_url
            -F $"master_pwd=($target_master_password)"
            -F $"name=($target_db)"
            -F $"backup_file=@($backup_file)"
            -F "copy=true"
            --silent
            --show-error
        )

        print $"✅ Restore completed successfully!"
        print $"🗃️ Database: ($target_db)"
        print $"🌐 Environment: ($target_environment)"

        # Nettoyer le fichier temporaire si créé
        if $from_env != null {
            rm $backup_file
            print $"🧹 Temporary backup file cleaned"
        }

    } catch { |e|
        print $"❌ Restore failed: ($e.msg)"
        print "💡 Check master password, database name and backup file"
        print "🔍 Debug: trying alternative method..."

        # Méthode alternative avec http post
        try {
            let backup_content = (open $backup_file)
            let form_data = {
                master_pwd: $target_master_password,
                name: $target_db,
                backup_file: $backup_content
            }

            http post $restore_url $form_data --content-type "multipart/form-data"
            print $"✅ Restore completed with alternative method!"

        } catch { |e2|
            print $"❌ Alternative method also failed: ($e2.msg)"
            print "💡 You may need to restore manually via Odoo interface"
        }

        # Nettoyer en cas d'erreur aussi
        if ($from_env != null and ($backup_file | path exists)) {
            rm $backup_file
        }
    }
}