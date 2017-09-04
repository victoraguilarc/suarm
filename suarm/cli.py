# -*- coding: utf-8 -*-

import click

from suarm.app.actions import deploy_app
from suarm.server.config import get_server_config

from .cluster.actions import (
    resize_server, destroy_server, register_sshkey,
    list_sshkeys, destroy_sshkey, create_cluster, setup_cluster,
    destroy_cluster, create_servers, setup_cluster_registry, setup_cluster_proxy,
    setup_cluster_dashboard, get_cluster_config, setup_cluster_as_alpha, show_cluster_docker_version, restart_cluster)

from .server.actions import (
    setup_server, clean_server, view_servers,
    restart_server, deploy_django_application,
    fix_permissions, add_remote_server, upload_key_to_server,
    reset_database, reset_environment, renew_ssl_certificates,
    createsuperuser)


@click.group(chain=True)
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
def main(config):
    click.echo("\nStarting...")


@main.command('node')
@click.option('--resize', '-r', is_flag=True, help='Upgrade plan of a node')
@click.option('--delete', '-d', is_flag=True, help='Delete a node')
@click.option('--plan', '-p', type=int, default=None, help='Resize a node')
@click.option('--subid', '-s', type=str, default=None, help='SUbID for node operations')
def node(resize, delete, plan, subid):
    settings, headers = get_cluster_config()
    if resize:
        click.echo('-- ON Resize...')
        if plan and subid:
            resize_server(subid, plan)
        else:
            click.echo('We need PlanID and SUBID of the node')
    elif delete:
        click.echo('-- ON Delete...')
        if subid:
            destroy_server(subid)
        else:
            click.echo('We need SUBID of the node')
    else:
        click.echo(settings["cluster"])


@main.command('keys')
@click.option('--create', '-g', is_flag=True, help='Generate and register an sshkey')
@click.option('--show', '-l', is_flag=True, help='List your sshkeys')
@click.option('--delete', '-d', is_flag=True, help='Delete ssh-key')
def keys(create, show, delete):
    if create:
        register_sshkey()
    elif show:
        list_sshkeys()
    elif delete:
        destroy_sshkey()
    else:
        list_sshkeys()


@main.command('cluster')
@click.option('--create', '-c', is_flag=True, help='Create a Cluster based on swarm.json')
@click.option('--setup', '-s', is_flag=True, help='Setup nodes [master] and [workers] in the cluster')
@click.option('--delete', '-d', is_flag=True, help='Delete a Current cluster')
@click.option('--add-worker', '-a', type=int, default=None, help='Add worker to cluster')
@click.option('--add-manager', '-a', type=int, default=None, help='Add manager to cluster')
@click.option('--setup-registry', '-sr', is_flag=True, help='Setup a REGISTRY in the cluster')
@click.option('--setup-proxy', '-sp', is_flag=True, help='Setup a PROXY FLOW in the cluster')
@click.option('--setup-dashboard', '-sd', is_flag=True, help='Setup PORTAINER and VISUALIZER in the cluster')
@click.option('--set-alpha', '-sa', is_flag=True, help='Setup all servers on alpha updates mode')
@click.option('--show-docker', '-vd', is_flag=True, help='Show Docker version')
@click.option('--restart', '-r', is_flag=True, help='Restart nodes in the cluster')
def cluster(create, setup, delete, add_worker, add_manager, setup_registry,
            setup_proxy, setup_dashboard, set_alpha, show_docker, restart):
    settings, headers = get_cluster_config()
    if create:
        create_cluster()
    elif setup:
        setup_cluster()
    elif delete:
        destroy_cluster()
    elif add_worker:
        create_servers(add_worker)
    elif add_manager:
        pass
    elif setup_registry:
        setup_cluster_registry()
    elif setup_proxy:
        setup_cluster_proxy()
    elif setup_dashboard:
        setup_cluster_dashboard()
    elif set_alpha:
        setup_cluster_as_alpha()
    elif show_docker:
        show_cluster_docker_version()
    elif restart:
        restart_cluster()
    else:
        click.echo(settings)


@main.command('setup')
@click.option('--service', type=click.Choice(['dashboard', 'manager', 'worker']))
@click.option('--subid', '-n', type=str, help='NodeID on Vultr')
def setup(service, subid):
    if service == 'dashboard':
        pass
    elif service == 'manager':
        pass
    elif service == 'worker':
        pass
    click.echo(service)


@main.command('loadbalancer')
@click.option('--create', '-c', is_flag=True, help='Create the load balancer')
@click.option('--delete', '-d', is_flag=True, help='Delete the load balancer')
@click.option('--setup', '-s', is_flag=True, help='Configure the load balancer')
def loadbalancer(create, delete, setup):
    if create:
        # TODO Implement for only one server
        pass
    elif setup:
        # TODO Implement for only one server
        pass
    elif delete:
        # TODO Implement for only one server
        pass


@main.command('server')
@click.option('--listing', '-l', is_flag=True, help='List servers in your vultr account')
@click.option('--setup', '-i', is_flag=True, help='Install and configure a server for')
@click.option('--clean', '-c', is_flag=True, help='Clean ans uninstall dependencies for ')
@click.option('--deploy', '-d', is_flag=True, help='Deploy current folder django app')
@click.option('--stage', '-s', type=str, default="production", help='Setup stage for django application')
@click.option('--fix-perms', '-fp', is_flag=True, help='Fix permissions for rpoject files in the server')
@click.option('--add-remote', '-ar', is_flag=True, help='Add remote git repo to local')
@click.option('--upload-keyfile', '-uk', is_flag=True, help='register your keyfile in your server if this allow it')
@click.option('--reset-db', '-rdb', is_flag=True, help='Reset Database')
@click.option('--reset-env', '-re', is_flag=True, help='Reset python project environment')
@click.option('--create-superuser', '-cs', is_flag=True, help='Create a superuser')
@click.option('--renew-certificates', '-rw', is_flag=True, help='Renew SSL Certificates')
@click.option('--restart', '-r', is_flag=True, help='Restart nodes in the cluster')
def server(listing, setup, clean, deploy, stage, fix_perms, add_remote, upload_keyfile,
           reset_db, reset_env, create_superuser, renew_certificates, restart):
    servers = get_server_config()
    if listing:
        print("\nLIST SERVERS\n")
        view_servers()
    elif setup:
        print("\nSETUP [%s] SERVER\n" % stage)
        setup_server(stage=stage)
    elif clean:
        print("\nCLEAN [%s] SERVER\n" % stage)
        clean_server(stage=stage)
    elif deploy:
        print("\nDEPLOY APP INTO [%s]\n" % stage)
        deploy_django_application(stage=stage)
    elif fix_perms:
        print("\nFIX PERMISSIONS [%s] SERVER\n" % stage)
        fix_permissions(stage=stage)
    elif add_remote:
        print("\nADD REMOTE [%s] SERVER\n" % stage)
        add_remote_server(stage=stage)
    elif upload_keyfile:
        print("\nUPLOAD [%s] SERVER\n" % stage)
        upload_key_to_server(stage=stage)
    elif reset_db:
        print("\nRESET DB INTO [%s]\n" % stage)
        reset_database(stage=stage)
    elif reset_env:
        print("\nRESET ENV [%s] SERVER\n" % stage)
        reset_environment(stage=stage)
    elif create_superuser:
        print("\nCREATE SUPERUSER IN [%s] SERVER\n" % stage)
        createsuperuser(stage=stage)
    elif renew_certificates:
        print("\nRENEW CERTIFICATES IN [%s]\n" % stage)
        renew_ssl_certificates(stage=stage)
    elif restart:
        restart_server(stage=stage)
    else:
        click.echo(servers)


@main.command('service')
@click.option('--deploy', '-d', is_flag=True, help='Deploy and application based on [docker-compose.yml]')
@click.option('--remove', '-r', is_flag=True, help='Remove and application based on [docker-compose.yml]')
def service(deploy, remove):
    if deploy:
        deploy_app()
    elif remove:
        pass
    else:
        pass