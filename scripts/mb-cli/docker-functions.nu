#!/usr/bin/env nu

use config.nu CONTAINERS

# Se connecter au container
export def connect [
    environment: string,           # Environnement (dev/staging/prod)
    service: string = "odoo",      # Service (odoo/db) - défaut: odoo
    ...command: string             # Commande à exécuter (optionnel)
] {
    # Reconstruction de la commande complète
    let full_command = if ($command | is-empty) {
        ""
    } else {
        $command | str join " "
    }

    try {
        let container_name = ($CONTAINERS | get $environment | get $service)

        match $service {
            "odoo" => {
                if ($full_command | is-empty) {
                    print $"🔗 Connecting to Odoo ($container_name)..."
                    docker exec -it $container_name bash
                } else {
                    print $"🚀 Executing command in Odoo ($container_name): ($full_command)"
                    docker exec $container_name bash -c $full_command
                }
            }
            "db" => {
                if ($full_command | is-empty) {
                    print $"🗄️ Connecting to Database ($container_name)..."
                    docker exec -it $container_name psql -U odoo -d multibikes
                } else {
                    print $"🗄️ Executing SQL in Database ($container_name): ($full_command)"
                    docker exec $container_name psql -U odoo -d multibikes -c $full_command
                }
            }
            _ => {
                error make {msg: $"❌ Unknown service: ($service). Available: odoo, db"}
            }
        }
    } catch {
        error make {msg: $"❌ Container not found or environment/service invalid. Available: dev/staging/prod + odoo/db"}
    }
}
# Construire les images Docker
export def build [
    target: string  # Target de build (prod/dev/staging/base/test/all)
] {
    cd /home/ngner/multibikes/odoo-deployment/

    match $target {
        "prod" => {
            print "🔨 Building prod image..."
            docker compose -f docker-compose_prod.yaml build
            print "✅ Prod image built!"
        }
        "dev" => {
            print "🔨 Building dev image..."
            docker compose -f docker-compose_dev.yaml build
            print "✅ Dev image built!"
        }
        "staging" => {
            print "🔨 Building staging image..."
            docker compose -f docker-compose_staging.yaml build
            print "✅ Staging image built!"
        }
        "base" => {
            print "🔨 Building base image..."
            docker compose -f docker-compose_base.yaml build
            print "✅ Base image built!"
        }
        "test" => {
            print "🧪 Building test image..."
            docker compose -f docker-compose_test.yaml build
            print "✅ Test image built!"
        }
        "all" => {
            print "🔨 Building all images (base + test)..."
            docker compose -f docker-compose_base.yaml build
            docker compose -f docker-compose_test.yaml build
            print "✅ All images built!"
        }
        _ => {
            error make {msg: $"❌ Unknown build target: ($target). Available: prod, dev, staging, base, test, all"}
        }
    }
}

# Arrêter la stack Docker
export def down [
    environment: string,           # Environnement (dev/staging/prod)
    --volumes(-v)   # Supprimer aussi les volumes
] {
    let compose_file = $"docker-compose_($environment).yaml"
    print $"🛑 Stopping ($environment) stack..."
    cd /home/ngner/multibikes/odoo-deployment/

    if $volumes {
        print "⚠️  Also removing volumes..."
        docker compose -f $compose_file down -v
    } else {
        docker compose -f $compose_file down
    }
    print $"✅ ($environment) stack stopped!"
}

# Démarrer la stack Docker
export def up [
    environment: string,           # Environnement (dev/staging/prod)
    --building(-b)     # Rebuild les images avant de démarrer
] {
    let compose_file = $"docker-compose_($environment).yaml"
    print $"🚀 Starting ($environment) stack..."
    cd /home/ngner/multibikes/odoo-deployment/

    if $building {
        print "🔨 Building images..."
        docker compose -f $compose_file up -d --build
    } else {
        docker compose -f $compose_file up -d
    }
    print $"✅ ($environment) stack started!"
}

# Redémarrer la stack
export def restart [
    environment: string           # Environnement (dev/staging/prod)
    --volumes(-v)  # Supprimer les volumes au down
    --build(-b)     # Rebuild au up
] {
    print $"🔄 Restarting ($environment) stack..."

    # Appel de vos autres fonctions avec les bons paramètres
    if $volumes {
        down $environment --volumes=true
    } else {
        down $environment
    }

    sleep 2sec  # Petite pause entre le down et le up

    if $build {
        up $environment --building=true
    } else {
        up $environment
    }

    print $"🎉 ($environment) stack restarted!"
}
# Afficher le statut des containers
export def status [
    environment?: string
] {
    if ($environment | is-empty) {
        print "📊 Status of all odoo containers:"
        dps "odoo"
    } else if $environment in ($CONTAINERS | columns) {
        print $"📊 Status of ($environment) containers:"
        let env_containers = ($CONTAINERS | get $environment | values)
        $env_containers | each { |container|
            print $"--- ($container) ---"
            dps $container
        }
    } else {
        let available_envs = ($CONTAINERS | columns | str join ', ')
        error make {msg: $"❌ Environment '($environment)' not found. Available: ($available_envs)"}
    }
}

# Afficher les logs
export def logs [
    environment: string          # Environnement (dev/staging/prod)
    service?: string            # Service spécifique (odoo/db) - optionnel
    --follow(-f)                # Suivre les logs en temps réel
    --tail(-n): int = 50        # Nombre de lignes à afficher (défaut: 50)
] {
    if ($service | is-empty) {
        # Afficher tous les containers de l'environnement
        let env_containers = ($CONTAINERS | get $environment | values)
        print $"📜 All logs for ($environment) environment $ last ($tail) lines each $ :"

        $env_containers | each { |container|
            print $"--- ($container) ---"
            try {
                docker logs --tail=$tail $container
            } catch {
                print $"❌ Container ($container) not found or not running"
            }
        }
    } else {
        # Afficher un service spécifique
        try {
            let container_name = ($CONTAINERS | get $environment | get $service)
            print $"📜 Logs for ($service) in ($environment): ($container_name)"

            if $follow {
                docker logs --tail=$tail -f $container_name
            } else {
                docker logs --tail=$tail $container_name
            }
        } catch {
            error make {msg: $"❌ Service ($service) not found in ($environment) environment"}
        }
    }
}
