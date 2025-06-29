#!/usr/bin/env nu

use docker-functions.nu *
use db-functions.nu *
use config.nu CONTAINERS

def main [
    command?: string,
    environment?: string,
    service?: string,
    --output (-o): string,
    --from-env (-e): string,
    --from-file (-f): string,
    --new-name (-n): string,
    --volumes (-v)
] {
    if $command == null {
        print "🚀 MultiBikes CLI - Docker & Database Management"
        print ""
        print "Usage: ./mb-cli.nu <command> [arguments] [options]"
        print ""
        print "Commands:"
        print "  connect     Connect to container"
        print "  logs        View container logs"
        print "  backup      Backup database"
        print "  restore     Restore database"
        print "  up          Start services"
        print "  down        Stop services"
        print "  restart     Restart services"
        print "  status      Show services status"
        print "  build       Build images"
        print ""
        print "Use './mb-cli.nu <command> --help' for detailed command help"
        print ""
        print "Examples:"
        print "  ./mb-cli.nu connect prod"
        print "  ./mb-cli.nu down dev --volumes"
        print "  ./mb-cli.nu backup prod"
        return
    }

    match $command {
        "restore" => {
            if $environment == null {
                print "❌ Please specify target environment: dev, staging, prod"
                return
            }
            restore $environment --from-env $from_env --from-file $from_file --new-name $new_name
        }
        "backup" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            backup $environment --output $output
        }
        "connect" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            connect $environment $service
        }
        "logs" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            logs $environment $service
        }
        "build" => {
            build $environment
        }
        "down" => {
            if $environment == null {
                print "❌ Please specify environment"
                return
            }
            if $volumes {
                down $environment --volumes  # Passer le flag
            } else {
                down $environment
            }
        }
        "up" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            up $environment
        }
        "restart" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            restart $environment
        }
        "status" => {
            if $environment == null {
                print "❌ Please specify environment: dev, staging, prod"
                return
            }
            status $environment
        }
        _ => {
            print $"❌ Unknown command: ($command)"
        }
    }
}



