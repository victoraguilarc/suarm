# -*- coding: utf-8 -*-
from .cluster import *

@click.group(chain=True)
def main():
    click.echo("\nStarting...")


@main.command('node')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--resize', '-r', is_flag=True, help='Upgrade plan of a node')
@click.option('--delete', '-d', is_flag=True, help='Delete a node')
@click.option('--plan', '-p', type=int, default=None, help='PlanID of the node')
@click.option('--subid', '-s', type=str, default=None, help='SubID of the node')
def node(config, resize, delete, plan, subid):
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
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--create', '-g', is_flag=True, help='Generate and register an sshkey')
@click.option('--show', '-l', is_flag=True, help='List your sshkeys')
@click.option('--delete', '-l', is_flag=True, help='List your sshkeys')
def keys(config, create, show, delete):
    if create:
        register_sshkey()
    elif show:
        list_sshkeys()
    elif delete:
        destroy_sshkey()
    else:
        list_sshkeys()



@main.command('cluster')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--create', '-c', is_flag=True, help='Create option')
@click.option('--delete', '-d', is_flag=True, help='Delete Option')
@click.option('--add-node', '-a', type=int, default=None, help='Delete Option')
def cluster(config, create, delete, add_node):
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
@click.option('--node', '-n', type=str, help='NodeID on Vultr')
def set(service, node):
    if service == 'dashboard':
        pass
    elif service == 'manager':
        pass
    elif service == 'worker':
        pass
    click.echo(service)


@main.command('loadbalancer')
@click.option('--config', '-f', type=click.Path(), help='Add load balancer')
@click.option('--create', '-c', is_flag=True, help='Delete or not')
@click.option('--delete', '-d', is_flag=True, help='Delete or not')
@click.option('--setup', '-s', is_flag=True, help='HTTPS support')
def loadbalancer(config, create, delete, setup):
    click.echo('--> Load balancer...')
    if create:
        add_loadbalancer()
    elif setup:
        setup_loadbalancer()
    elif delete:
        destroy_loadbalancer()


@main.command('app')
@click.option('--config', '-f', type=click.Path(), help='Add load balancer')
@click.option('--create', '-c', is_flag=True, help='Create option')
@click.option('--delete', '-d', is_flag=True, help='Delete Option')
def app(config, create, delete):
    click.echo('--> Load balancer...')
    if create:
        click.echo('--> CREATE')
    elif delete:
        click.echo('--> DELETE')
