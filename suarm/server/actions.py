
import requests
import click
from time import sleep

from click import prompt
from fabric.operations import local
from fabric.state import env
from fabric.tasks import execute

from ..cluster.actions import (
    create_server, SLEEP_TIME,
    register_ip, save_on_config, API_ENDPOINT,
    DESTROY_SERVER, config_env,
    get_cluster_config)
from ..server.config import set_user, set_stage
from ..server.project import Project
from ..server.server import Server


def add_node(tag, plan=201, oss="COREOS", zone="SILICON_VALLEY"):
    """
      Defaults:
        plan = 1GB RAM / 1CPU
        os = CoreOS
        zone = Silicon Valley
    """
    settings, headers = get_cluster_config()
    if tag in settings:
        if "SUBID" in settings[tag] and "ipv4" in settings[tag]:
            create = input("Are your sure to (re)create this? (y/N) : ")
            if create != 'y' and create != 'Y':
                click.echo("\n----> You are wise!")
                return False
        if "zone" in settings[tag]:
            zone = settings[tag]["zone"]

        if "plan" in settings[tag]:
            plan = settings[tag]["plan"]

        if "os" in settings[tag]:
            oss = settings[tag]["os"]
    else:
        settings[tag] = dict()

    success = create_server(zone=zone, plan=plan, oss=oss, label="%s-%s" % (settings["label"], tag), tag=tag)
    if "SUBID" in settings[tag] and success:
        sleep(SLEEP_TIME)
        settings[tag]["ipv4"] = register_ip(settings[tag]["SUBID"])
        save_on_config(tag, settings[tag])

    return success


def del_node(tag):
    settings, headers = get_cluster_config()
    if tag in settings and "SUBID" in settings[tag]:
        payload = {'SUBID': settings[tag]["SUBID"]}
        req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
        if req.status_code == 200:
            settings[tag] = {}
            save_on_config(tag, settings[tag])
            click.echo("\n--> Server %s deleted!!" % tag)
            return True
        else:
            click.echo("\n--> Couldn't create server!!")
            return False
    else:
        click.echo("\n--> Load %s improperly configured!!" % tag)
        return False


def setup_loadbalancer():
    settings, headers = get_cluster_config()
    if "loadbalancer" in settings and "ipv4" in settings["loadbalancer"]:
        config_env()
        execute(Server.deps, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.haproxy, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.letsencrypt, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.reboot, hosts=[settings["loadbalancer"]["ipv4"]])


# ~$ COMMANDS
# ---------------------------------------------------------------------
def upgrade_server():
    set_user(superuser=True)
    execute(Server.upgrade, hosts=env.hosts)


def setup_server(stage="production"):
    """
    Install app in selected server(s).
    """
    set_stage(stage)
    set_user(superuser=True)
    execute(Server.deps, hosts=env.hosts)
    execute(Server.user, hosts=env.hosts)
    execute(Server.group, hosts=env.hosts)
    execute(Server.create_db, hosts=env.hosts)
    execute(Server.git, hosts=env.hosts)
    execute(Server.add_remote, hosts=env.hosts)
    execute(Server.web_server, hosts=env.hosts)
    execute(Server.gunicorn, hosts=env.hosts)
    execute(Server.supervisor, hosts=env.hosts)
    execute(Server.letsencrypt, hosts=env.hosts)
    execute(Server.var, hosts=env.hosts)
    execute(Server.pip_cache, hosts=env.hosts)
    execute(Server.fix_permissions, hosts=env.hosts)


def clean_server(stage="production"):
    """
    Uninstall app in selected server(s)
    """
    set_stage(stage)
    set_user(superuser=True)
    execute(Server.clean, hosts=env.hosts)


def restart_server(stage="production"):
    """
    Restart all app services.
    """
    set_stage(stage)
    set_user(superuser=True)
    execute(Server.restart_services, hosts=env.hosts)


def view_servers():
    """
    List your own servers

    """
    pass


def deploy_django_application(stage="production"):
    """
    Deploy application in selected server(s)
    """
    set_stage(stage)
    set_user()
    execute(Project.push, hosts=env.hosts)
    execute(Project.environment, hosts=env.hosts)
    execute(Project.install, hosts=env.hosts)
    execute(Project.clean, hosts=env.hosts)


def fix_permissions(stage="production"):
    """
    Add project repo url to local git configuration.
    """
    set_stage(stage)
    set_user(superuser=True)
    execute(Server.fix_permissions, hosts=env.hosts)


def add_remote_server(stage="production"):
    """
    Add project repo url to local git configuration.
    """
    set_stage(stage)
    set_user()
    execute(Server.add_remote, hosts=env.hosts)


def upload_key_to_server(stage="production"):
    """
    Upload SSH key to server.
    """
    set_stage(stage)
    set_user()
    execute(Project.upload_key, hosts=env.hosts)


def reset_database(stage="production"):
    """
    Reset the env Database
    """
    set_stage(stage)
    reset = prompt("Reset Database, Are you sure? (y/N)", default="N")

    if reset == 'y' or reset == 'Y':
        set_user(superuser=True)
        execute(Server.reset_db, hosts=env.hosts)


def reset_environment(stage="production"):
    """
    Reset the python env
    """
    set_stage(stage)
    reset = prompt("Reset environment, Are you sure? (y/N)", default="N")

    if reset == 'y' or reset == 'Y':
        set_user(superuser=True)
        execute(Project.reset_env, hosts=env.hosts)


def createsuperuser(stage="production"):
    """
    Create a project superuser in selected server(s).
    """
    set_stage(stage)
    set_user(superuser=True)
    execute(Project.create_superuser, hosts=env.hosts)


def setup_server_language():
    local("echo \"export LANG=C.UTF-8\" >> ~/.bash_profile")
    local("echo \"export LC_CTYPE=C.UTF-8\" >> ~/.bash_profile")
    local("echo \"export LC_ALL=C.UTF-8\" >> ~/.bash_profile")


def make_backup(stage="production"):
    set_stage(stage)
    set_user(superuser=True)
    with settings(hide('warnings'), warn_only=True, ):
        execute(Project.backup, hosts=env.hosts)
        execute(Project.download_backup, hosts=env.hosts)

def renew_ssl_certificates(stage="production"):
    set_stage(stage)
    set_user(superuser=True)

    if env.domain:
        execute(Server.letsencrypt, hosts=env.hosts)
    else:
        raise Exception("[domain] is reuired into [%s] server configuration" % env.stage)
