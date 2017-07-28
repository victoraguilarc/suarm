# -*- coding: utf-8 -*-
from .cluster import *

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
@click.option('--delete', '-d', is_flag=True, help='Delete a Current cluster')
@click.option('--add-node', '-a', type=int, default=None, help='Add worker to cluster')
def cluster(create, delete, add_node):
    if create:
        create_cluster()
    elif delete:
        destroy_cluster()
    elif add_node:
        create_servers(add_node)
    else:
        click.echo(settings)


@main.command('set')
@click.option('--service', type=click.Choice(['dashboard', 'manager', 'worker']))
@click.option('--subid', '-n', type=str, help='NodeID on Vultr')
def set(service, subid):
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
        add_loadbalancer()
    elif setup:
        setup_loadbalancer()
    elif delete:
        destroy_loadbalancer()


@main.command('app')
@click.option('--create', '-c', is_flag=True, help='Register an app for deploy in the cluster')
@click.option('--delete', '-d', is_flag=True, help='Delete an app from de cluster')
def app(create, delete):
    click.echo('--> Load balancer...')
    if create:
        click.echo('--> CREATE')
    elif delete:
        click.echo('--> DELETE')
