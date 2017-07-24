# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import, print_function
from .cluster import *


@click.group(chain=True)
def main():
    click.echo("Starting...")


@main.command('nodes')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
def nodes(config):
    click.echo('nodes')


@main.command('scale')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--node', '-n', type=str, help='NodeID on Vultr')
@click.option('--plan', '-p', type=str, help='PlanID on Vultr')
def scale(config, node, plan):
    click.echo('scale')


@main.command('ssh-keygen')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
def ssh_keygen(config):
    click.echo('ssh_keygen')
    register_sshkey()


@main.command('swarm')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--create', '-c', is_flag=True, help='Create option')
@click.option('--delete', '-d', is_flag=True, help='Delete Option')
@click.option('--add-node', '-a', type=int, default=None, help='Delete Option')
def swarm(config, create, delete, add_node):
    if create:
        create_cluster()
    elif delete:
        destroy_cluster()
    elif add_node:
        create_servers(add_node)
    else:
        click.echo(settings)


@main.command('increase')
@click.option('--config', '-f', type=click.Path(), help='Config file "swarm.json"')
@click.option('--replicas', '-r', type=int, help='NodeID on Vultr')
@click.option('--plan', '-p', type=str, help='PlanID on Vultr')
@click.option('--os', '-o', type=str, help='OSID on Vultr')
def increase(config, replicas, plan, os):
    click.echo('increase')


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
@click.option('--create', is_flag=True, help='Delete or not')
@click.option('--delete', is_flag=True, help='Delete or not')
@click.option('--setup', is_flag=True, help='HTTPS support')
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




