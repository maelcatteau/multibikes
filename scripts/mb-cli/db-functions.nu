#!/usr/bin/env nu

use config.nu CONTAINERS

# Fonction utilitaire pour parser la config Odoo
def parse_odoo_config [config_content: string] {
    $config_content
    | lines
    | where {|line| not ($line | str starts-with "#") and not ($line | str trim | is-empty)}
    | parse "{key} = {value}"
    | reduce -f {} {|it, acc| $acc | insert $it.key $it.value}
}
export def backup [
    environment: string,  # Environnement (dev/staging/prod)
    database: string      # Base de données à sauvegarder
] {
    # Configuration des chemins
    let backup_base_dir = "/home/ngner/multibikes/odoo-deployment/backups"
    let backup_env_dir = $"($backup_base_dir)/($environment)"
    let timestamp = (date now | format date "%Y%m%d_%H%M%S")
    let backup_filename = $"($database)_backup_($timestamp)"

    # Créer le répertoire de backup pour l'environnement
    mkdir $backup_env_dir

    print "🚀 SAUVEGARDE ODOO"
    print "============================================"
    print $"📋 Environnement   : ($environment)"
    print $"📋 Base de données : ($database)"
    print $"📋 Dossier        : ($backup_env_dir)"
    try {
        let container = ($CONTAINERS | get $environment | get odoo)
        print $"📋 Conteneur       : ($container)"

        # Vérifier que le conteneur existe et tourne
        let container_check = (docker ps -q -f $"name=^($container)$" | complete)
        if ($container_check.stdout | str trim | is-empty) {
            error make {msg: $"❌ Le conteneur '($container)' n'existe pas ou n'est pas démarré"}
        }

        # Récupérer et parser la configuration Odoo
        print "🔍 Récupération de la configuration de base de données..."
        let config_result = (connect $environment odoo "cat /etc/odoo/odoo.conf" | complete)

        if $config_result.exit_code != 0 {
            error make {msg: "❌ Impossible de récupérer la configuration Odoo"}
        }

        let odoo_config = (parse_odoo_config $config_result.stdout)

        let db_host = ($odoo_config | get db_host? | default "localhost")
        let db_port = ($odoo_config | get db_port? | default "5432")
        let db_user = ($odoo_config | get db_user? | default "odoo")
        let db_password = ($odoo_config | get db_password? | default "")

        if ($db_password | is-empty) {
            error make {msg: "❌ Mot de passe de base de données introuvable dans la configuration"}
        }

        print $"🔍 Connexion DB : ($db_user)@($db_host):($db_port)"

        # Créer le dump PostgreSQL
        print "💾 Création du dump PostgreSQL..."
        let dump_command = $"PGPASSWORD='($db_password)' pg_dump -h '($db_host)' -p '($db_port)' -U '($db_user)' -d \"($database)\" -f /tmp/($backup_filename).sql"
        let dump_result = (connect $environment odoo $dump_command | complete)

        if $dump_result.exit_code != 0 {
            error make {msg: $"❌ Échec du dump PostgreSQL: ($dump_result.stderr)"}
        }

        # Créer l'archive du filestore si le répertoire existe
        let filestore_path = $"/var/lib/odoo/filestore/($database)"
        let filestore_check = (connect $environment odoo $"[ -d \"($filestore_path)\" ] && echo exists" | complete)

        if ($filestore_check.stdout | str trim) == "exists" {
            print "📁 Archivage du filestore..."
            let filestore_command = $"cd /var/lib/odoo && tar -czf /tmp/($backup_filename)_filestore.tar.gz filestore/($database)/"
            let filestore_result = (connect $environment odoo $filestore_command | complete)
            if $filestore_result.exit_code != 0 {
                print $"⚠️ Avertissement : Échec de l'archivage du filestore: ($filestore_result.stderr)"
            }
        } else {
            print "📁 Aucun filestore trouvé, création d'un répertoire vide..."
            connect $environment odoo $"mkdir -p /tmp/empty_filestore/($database) && cd /tmp && tar -czf /tmp/($backup_filename)_filestore.tar.gz empty_filestore/ && rm -rf empty_filestore"
        }

        # Créer l'archive finale combinant SQL et filestore
        print "📦 Création de l'archive finale..."
        let archive_command = $"cd /tmp && tar -czf ($backup_filename).tar.gz ($backup_filename).sql ($backup_filename)_filestore.tar.gz"
        let archive_result = (connect $environment odoo $archive_command | complete)

        if $archive_result.exit_code != 0 {
            error make {msg: $"❌ Échec de la création de l'archive finale: ($archive_result.stderr)"}
        }

        # Vérifier que l'archive finale existe
        let archive_check = (connect $environment odoo $"ls -la /tmp/($backup_filename).tar.gz" | complete)
        if $archive_check.exit_code != 0 {
            error make {msg: $"❌ Archive finale non trouvée: ($archive_check.stderr)"}
        }

        print $"📋 Archive créée : ($archive_check.stdout)"

        # Copier l'archive vers l'hôte
        print "📋 Copie de l'archive vers l'hôte..."
        let backup_path = $"($backup_env_dir)/($backup_filename).tar.gz"
        let copy_result = (docker cp $"($container):/tmp/($backup_filename).tar.gz" $backup_path | complete)

        if $copy_result.exit_code != 0 {
            error make {msg: $"❌ Échec de la copie: ($copy_result.stderr)"}
        }

        # Nettoyer les fichiers temporaires
        print "🧹 Nettoyage..."
        connect $environment odoo $"rm -f /tmp/($backup_filename)*"

        # Afficher les résultats
        print ""
        print "🎉 SAUVEGARDE TERMINÉE !"
        print "============================================"
        print $"📄 Fichier : ($backup_path)"

        # Calculer la taille du fichier
        if ($backup_path | path exists) {
            let file_info = (ls $backup_path | get 0)
            let size = ($file_info.size | into string)
            print $"📊 Taille : ($size)"
        }

        print ""
        print "💡 Commandes suivantes possibles :"
        print $"   mb restore ($environment) ($backup_filename).tar.gz <target_db>"
        print $"   mb list_backups ($environment)"

    } catch { |e|
        print $"❌ Erreur lors de la sauvegarde : ($e.msg)"
    }
}
export def list_backups [
    environment: string  # Environnement (dev/staging/prod)
] {
    let backup_dir = $"/home/ngner/multibikes/odoo-deployment/backups/($environment)"

    if not ($backup_dir | path exists) {
        print $"📂 Aucune sauvegarde trouvée pour ($environment)"
        return
    }

    print $"📦 Sauvegardes disponibles pour ($environment) :"
    print "============================================"

    let backups = (ls $backup_dir | where type == file and name =~ ".*\\.tar\\.gz$" | sort-by modified | reverse)

    if ($backups | length) == 0 {
        print "📂 Aucune sauvegarde .tar.gz trouvée"
    } else {
        $backups | each { |backup|
            let filename = ($backup.name | path basename)
            let size = ($backup.size | into string)
            let date = ($backup.modified | format date "%Y-%m-%d %H:%M:%S")
            print $"📦 ($filename) - ($size) - ($date)"
        }
    }
}
export def restore [
    environment: string,      # Environnement (dev/staging/prod)
    backup_file: string,      # Fichier de backup (.tar.gz)
    target_database: string   # Base de données de destination
] {
    # Configuration des chemins
    let backup_base_dir = "/home/ngner/multibikes/odoo-deployment/backups"
    let backup_path = if ($backup_file | path exists) {
        $backup_file
    } else {
        $"($backup_base_dir)/($environment)/($backup_file)"
    }

    print "🔄 RESTAURATION ODOO"
    print "============================================"
    print $"📋 Environnement   : ($environment)"
    print $"📋 Base de données : ($target_database)"
    print $"📋 Backup          : ($backup_file | path basename)"

    # Vérifications
    if not ($backup_path | path exists) {
        error make {msg: $"❌ Fichier de sauvegarde introuvable : ($backup_path)"}
    }

    try {
        let container = ($CONTAINERS | get $environment | get odoo)
        print $"📋 Conteneur       : ($container)"

        # Vérifier que le conteneur existe et tourne
        let container_check = (docker ps -q -f $"name=^($container)$" | complete)
        if ($container_check.stdout | str trim | is-empty) {
            error make {msg: $"❌ Le conteneur '($container)' n'existe pas ou n'est pas démarré"}
        }

        # Confirmation
        print ""
        print "⚠️  ATTENTION ⚠️"
        print "Cette opération va :"
        print $"   🗑️  SUPPRIMER la base '($target_database)' si elle existe"
        print $"   📦 RESTAURER depuis ($backup_file | path basename)"
        print ""
        print "Continuer ? (tapez 'OUI')"

        let confirm = (input)
        if $confirm != "OUI" {
            print "🛑 Restauration annulée"
            return
        }

        # Récupérer la configuration DB
        print "🔍 Récupération de la configuration..."
        let config_result = (connect $environment odoo "cat /etc/odoo/odoo.conf" | complete)

        if $config_result.exit_code != 0 {
            error make {msg: "❌ Impossible de récupérer la configuration Odoo"}
        }

        let odoo_config = (parse_odoo_config $config_result.stdout)

        let db_host = ($odoo_config | get db_host? | default "localhost")
        let db_port = ($odoo_config | get db_port? | default "5432")
        let db_user = ($odoo_config | get db_user? | default "odoo")
        let db_password = ($odoo_config | get db_password? | default "")

        if ($db_password | is-empty) {
            error make {msg: "❌ Mot de passe de base de données introuvable"}
        }

        # Arrêter Odoo
        print "🛑 Arrêt d'Odoo..."
        let stop_result = (docker stop $container | complete)
        if $stop_result.exit_code != 0 {
            error make {msg: "❌ Impossible d'arrêter le conteneur"}
        }

        # Copier le backup
        let timestamp = (date now | format date "%s")
        let temp_backup = $"/tmp/restore_($timestamp).tar.gz"
        print "📋 Copie de l'archive..."
        docker cp $backup_path $"($container):($temp_backup)"

        # Démarrer temporairement le conteneur
        print "🚀 Démarrage temporaire du conteneur..."
        docker start $container
        sleep 5sec

        # Extraire l'archive
        print "📦 Extraction de l'archive..."
        let extract_result = (connect $environment odoo $"cd /tmp && tar -xzf ($temp_backup)" | complete)
        if $extract_result.exit_code != 0 {
            error make {msg: $"❌ Échec de l'extraction: ($extract_result.stderr)"}
        }

        # Identifier les fichiers
        let sql_file_result = (connect $environment odoo "ls /tmp/*_backup_*.sql 2>/dev/null | head -1" | complete)
        let filestore_result = (connect $environment odoo "ls /tmp/*_filestore.tar.gz 2>/dev/null | head -1" | complete)

        if $sql_file_result.exit_code != 0 or ($sql_file_result.stdout | str trim | is-empty) {
            error make {msg: "❌ Fichier SQL introuvable dans l'archive"}
        }

        let sql_file = ($sql_file_result.stdout | str trim)
        let filestore_archive = if $filestore_result.exit_code == 0 {
            ($filestore_result.stdout | str trim)
        } else {
            ""
        }

        # Supprimer la base existante
        print "🗑️ Suppression de la base existante..."
        let drop_command = $"PGPASSWORD='($db_password)' psql -h '($db_host)' -p '($db_port)' -U '($db_user)' -d postgres -c \"DROP DATABASE IF EXISTS \\\"($target_database)\\\"\""
        connect $environment odoo $drop_command

        # Créer la nouvelle base
        print "🆕 Création de la nouvelle base..."
        let create_command = $"PGPASSWORD='($db_password)' psql -h '($db_host)' -p '($db_port)' -U '($db_user)' -d postgres -c \"CREATE DATABASE \\\"($target_database)\\\" WITH OWNER \\\"($db_user)\\\" ENCODING 'UTF8'\""
        let create_result = (connect $environment odoo $create_command | complete)
        if $create_result.exit_code != 0 {
            error make {msg: $"❌ Échec de la création de base: ($create_result.stderr)"}
        }

        # Restaurer le dump SQL
        print "💾 Restauration du dump SQL..."
        let restore_command = $"PGPASSWORD='($db_password)' psql -h '($db_host)' -p '($db_port)' -U '($db_user)' -d \"($target_database)\" -f ($sql_file)"
        let restore_result = (connect $environment odoo $restore_command | complete)
        if $restore_result.exit_code != 0 {
            error make {msg: $"❌ Échec de la restauration SQL: ($restore_result.stderr)"}
        }

        # Restaurer le filestore si disponible
        if not ($filestore_archive | is-empty) {
            print "📁 Restauration du filestore..."
            # D'abord, créer le répertoire de destination et nettoyer
            connect $environment odoo $"mkdir -p /var/lib/odoo/filestore && rm -rf /var/lib/odoo/filestore/($target_database)"

            # Extraire dans un répertoire temporaire pour examiner la structure
            connect $environment odoo $"mkdir -p /tmp/filestore_extract"
            connect $environment odoo $"cd /tmp/filestore_extract && tar -xzf ($filestore_archive)"

            # Vérifier la structure et copier correctement
            let structure_check = (connect $environment odoo "ls -la /tmp/filestore_extract/" | complete)
            print $"🔍 Structure du filestore : ($structure_check.stdout)"

            # Si la structure contient déjà 'filestore/', utiliser directement
            let has_filestore_dir = (connect $environment odoo "[ -d \"/tmp/filestore_extract/filestore\" ] && echo yes || echo no" | complete)

            if ($has_filestore_dir.stdout | str trim) == "yes" {
                # Structure correcte : filestore/database/
                connect $environment odoo $"mkdir -p /var/lib/odoo/filestore/($target_database) && cp -r /tmp/filestore_extract/filestore/*/* /var/lib/odoo/filestore/($target_database)/ 2>/dev/null || cp -r /tmp/filestore_extract/filestore/* /var/lib/odoo/filestore/($target_database)/ && chown -R odoo:odoo /var/lib/odoo/filestore/($target_database)"
            } else {
                # Structure directe : fichiers directement dans l'archive
                connect $environment odoo $"mkdir -p /var/lib/odoo/filestore/($target_database) && cp -r /tmp/filestore_extract/* /var/lib/odoo/filestore/($target_database)/ && chown -R odoo:odoo /var/lib/odoo/filestore/($target_database)"
            }


            # Corriger les permissions
            connect $environment odoo $"chown -R odoo:odoo /var/lib/odoo/filestore/($target_database) 2>/dev/null || true"

            # Nettoyer le répertoire temporaire
            connect $environment odoo $"rm -rf /tmp/filestore_extract"
        }


        # Nettoyer (version améliorée)
        print "🧹 Nettoyage..."
        connect $environment odoo $"rm -f /tmp/*_backup_* /tmp/*_filestore.tar.gz 2>/dev/null || true"
        # Le fichier temporaire de restore sera nettoyé par le système


        # Redémarrer Odoo
        print "🚀 Redémarrage d'Odoo..."
        docker restart $container

        print "⏳ Attente du démarrage (5 secondes)..."
        sleep 5sec

        print ""
        print "🎉 RESTAURATION TERMINÉE !"
        print "============================================"
        print $"✅ Base '($target_database)' restaurée depuis ($backup_file | path basename)"
        print ""
        print "💡 Commandes suivantes possibles :"
        print $"   mb connect ($environment) odoo"
        print $"   mb backup ($environment) ($target_database)"

    } catch { |e|
        print $"❌ Erreur lors de la restauration : ($e.msg)"
        # Tentative de redémarrage du conteneur en cas d'erreur
        try {
            let container = ($CONTAINERS | get $environment | get odoo)
            docker start $container
        }
    }
}

export def transfer [
    source_env: string,      # Environnement source (dev/staging/prod)
    target_env: string,      # Environnement de destination (dev/staging uniquement)
    database: string         # Base de données à transférer
] {
    print "🔄 TRANSFERT DE BASE DE DONNÉES"
    print "============================================"
    print $"📋 Source      : ($source_env)"
    print $"📋 Destination : ($target_env)"
    print $"📋 Database    : ($database)"
    print ""

    # Sécurité : Interdire de pousser vers la production
    if $target_env == "prod" {
        print "🚫 TRANSFERT INTERDIT !"
        print "============================================"
        print "❌ Il est interdit de transférer des données vers la production"
        print "💡 La production ne peut recevoir des données que via 'restore' manuel"
        print ""
        print "✅ Transferts autorisés :"
        print "   • prod → staging (pull depuis prod)"
        print "   • prod → dev (pull depuis prod)"
        print "   • staging → dev (pull depuis staging)"
        error make {msg: "Transfert vers la production interdit"}
    }

    # Vérifier que les environnements sont différents
    if $source_env == $target_env {
        error make {msg: "❌ L'environnement source et destination doivent être différents"}
    }

    # Vérifier que la base source existe
    print "🔍 Vérification de la base source..."
    let source_dbs = (list_db $source_env)
    if not ($database in $source_dbs) {
        error make {msg: $"❌ La base de données '($database)' n'existe pas dans l'environnement ($source_env)"}
    }
    print "✅ Base source trouvée"

    # Vérifier si la base destination existe et alerter
    let target_dbs = (list_db $target_env)
    if ($database in $target_dbs) {
        print "⚠️  ATTENTION !"
        print "============================================"
        print $"⚠️  La base '($database)' existe déjà dans ($target_env)"
        print "⚠️  Elle sera ÉCRASÉE par les données de ($source_env)"
        print ""
    }

    # Demande de confirmation
    print "🤔 CONFIRMATION REQUISE"
    print "============================================"
    print $"Voulez-vous transférer '($database)' de ($source_env) vers ($target_env) ?"
    if ($database in $target_dbs) {
        print $"⚠️  ATTENTION: Cela ÉCRASERA la base existante dans ($target_env) !"
    }
    print ""
    print "Tapez 'OUI' en majuscules pour confirmer, ou n'importe quoi d'autre pour annuler:"

    let confirmation = (input)

    if $confirmation != "OUI" {
        print "❌ Transfert annulé par l'utilisateur"
        return
    }

    print ""
    print "🚀 DÉBUT DU TRANSFERT"
    print "============================================"

    try {
        # Étape 1: Créer un backup de la source
        print "📦 Étape 1/3: Sauvegarde de la source..."
        backup $source_env $database

        # Étape 2: Trouver le backup le plus récent créé
        print "🔍 Recherche du backup créé..."
        let backup_dir = $"/home/ngner/multibikes/odoo-deployment/backups/($source_env)"
        let latest_backup = (ls $backup_dir
            | where type == file and name =~ $"($database)_backup_.*\\.tar\\.gz$"
            | sort-by modified
            | last
            | get name
            | path basename)

        print $"✅ Backup identifié: ($latest_backup)"

        # Étape 3: Copier le backup vers la destination et restaurer
        print "🔄 Étape 2/3: Copie et restauration vers la destination..."
        let target_backup_dir = $"/home/ngner/multibikes/odoo-deployment/backups/($target_env)"
        mkdir $target_backup_dir
        cp $"($backup_dir)/($latest_backup)" $"($target_backup_dir)/($latest_backup)"

        restore $target_env $latest_backup $database

        # Étape 4: Vérification
        print "🔍 Étape 3/3: Vérification du transfert..."

        print ""
        print "🎉 TRANSFERT RÉUSSI !"
        print "============================================"
        print $"✅ Base '($database)' transférée de ($source_env) vers ($target_env)"
        print $"📦 Backup conservé dans les deux environnements"
        print ""
        print "💡 Commandes utiles :"
        print $"   mb connect ($target_env) odoo"
        print $"   mb list_db ($target_env)"

    } catch { |e|
        print ""
        print "❌ ERREUR DURANT LE TRANSFERT"
        print "============================================"
        print $"❌ Erreur: ($e.msg)"
        print ""
        print "🔧 Actions recommandées :"
        print "   1. Vérifier que les containers sont démarrés"
        print $"   2. mb list_backups ($source_env)  # Vérifier les backups"
        print $"   3. Restauration manuelle si nécessaire"
    }
}
# Récupérer la configuration de base de données d'un environnement
def get_db_config [
    environment: string          # Environnement (dev/staging/prod)
] {
    print "🔍 Récupération de la configuration..."
    let config_result = (connect $environment odoo "cat /etc/odoo/odoo.conf" | complete)

    if $config_result.exit_code != 0 {
        error make {msg: "❌ Impossible de récupérer la configuration Odoo"}
    }

    let odoo_config = (parse_odoo_config $config_result.stdout)

    return {
        db_host: ($odoo_config | get db_host? | default "localhost"),
        db_port: ($odoo_config | get db_port? | default "5432"),
        db_user: ($odoo_config | get db_user? | default "odoo"),
        db_password: ($odoo_config | get db_password? | default "")
    }
}
# Lister les bases de données d'un environnement
export def list_db [
    environment: string          # Environnement (dev/staging/prod)
] {
    # Vérification que l'environnement existe
    if not ($environment in ($CONTAINERS | columns)) {
        error make {msg: $"❌ Environnement '($environment)' non reconnu. Environnements disponibles: ($CONTAINERS | columns | str join ', ')"}
    }

    # Récupération du container DB
    let db_container = try {
        $CONTAINERS | get $environment | get db
    } catch {
        error make {msg: $"❌ Container de base de données non configuré pour l'environnement ($environment)"}
    }

    # Vérification que le container est en cours d'exécution
    let running_containers = (docker ps --format "{{.Names}}" | lines)
    if not ($db_container in $running_containers) {
        error make {msg: $"❌ Le container ($db_container) n'est pas en cours d'exécution"}
    }

    try {
        # Récupérer la configuration DB via ta fonction
        let db_config = (get_db_config $environment)

        # Vérifier que le mot de passe est disponible
        if ($db_config.db_password | is-empty) {
            error make {msg: "❌ Mot de passe de base de données non trouvé dans la configuration"}
        }

        # Construire la commande SQL pour lister les bases de données
        let sql_command = "SELECT datname FROM pg_database WHERE datistemplate = false AND datname NOT IN ('postgres');"

        print $"🔗 Connexion à la base de données ($db_config.db_host):($db_config.db_port)..."

        # Exécuter la commande avec le mot de passe
        let list_result = (docker exec -e $"PGPASSWORD=($db_config.db_password)" $db_container psql -h $db_config.db_host -p $db_config.db_port -U $db_config.db_user -d postgres -t -c $sql_command | complete)

        if $list_result.exit_code != 0 {
            error make {msg: $"❌ Erreur lors de l'exécution de la requête SQL: ($list_result.stderr)"}
        }

        # Traiter le résultat
        let db_list = ($list_result.stdout | lines | str trim | where $it != "" and $it != "postgres")

        if ($db_list | length) == 0 {
            print "📋 Aucune base de données utilisateur trouvée"
            return []
        }

        print $"📋 Bases de données trouvées: ($db_list | length)"
        return $db_list

    } catch { |err|
        error make {msg: $"❌ Impossible de lister les bases de données pour l'environnement ($environment): ($err.msg)"}
    }
}