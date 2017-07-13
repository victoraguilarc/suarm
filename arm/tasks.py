from __future__ import unicode_literals
import os, json

from fabric.api import *
from fabric.contrib.files import exists, upload_template
from fabric.operations import local, prompt
from fabric.state import env

from getpass import getpass




# ~$ PATH - CONFIGURATION
# ---------------------------------------------------------------------

SERVERS_FILE = "servers.json"
DIGITALOCEAN_FILE = "digitalocean.json"
HOME_PATH = "/webapps"

DB_MYSQL = "mysql"
DB_POSTGRESQL = "postgresql"
DB_SQLITE = "sqlite"


try:
    sfile = open(SERVERS_FILE, 'r')
    SERVERS = json.load(sfile)
except Exception as e:
    raise Exception('servers.json file required!')


def get_config(stage="develop"):
    for server in SERVERS:
        if type(server) is dict and "name" in server and server["name"] == stage:
            if type(server["settings"]) is dict:
                return server["settings"]
    raise Exception('Malformed servers.json configuration.')


def get_digitalocean_config():
    try:
        import digitalocean
        sfile = open(DIGITALOCEAN_FILE, 'r')
        config = json.load(sfile)
        manager = digitalocean.Manager(token=config["token"])
        return config, manager
    except Exception as e:
        raise Exception('digitalocean.json file required!')


def make_user(project):
    return "%s_user" % project


def make_team(project):
    return "%s_team" % project


def make_app(project):
    return "%s_app" % project


def get_user_home(stage="develop"):
    return "%(home_path)s/%(user)s" % {
        "home_path": HOME_PATH,
        "user": make_user(SERVERS[stage]["project"]),
    }


def get_project_path(stage="develop"):
    return "%(user_home)s/%(project)s" % {
        "user_home": get_user_home(stage),
        "project": make_app(SERVERS[stage]["project"]),
    }


def get_project_src(stage="develop"):
    return "%(user_home)s/%(project)s/src" % {
        "user_home": get_user_home(stage),
        "project": make_app(SERVERS[stage]["project"]),
    }


def get_superuser():
    username = SERVERS[env.stage]["superuser"]
    password = getpass("Put password for [%s]" % username)
    if len(password) == 0:
        print("[vagrant] default password setted")
        password = "vagrant"

    return username, password


def _upload_key():
    """
    Upload  id_rsa.pub file to server.
    This file is obtained from ssh-keygen command.
    """
    try:
        local("ssh-copy-id %(user)s@%(ip_addres)s" % {
            "user": make_user(env.project),
            "ip_addres": env.ip
        })
    except Exception as e:
        raise Exception('Unfulfilled local requirements')


def set_stage(stage='develop'):
    if stage in SERVERS.keys():
        env.stage = stage
        env.project = SERVERS[env.stage]["project"]
        env.domain = SERVERS[env.stage]["domain"]
        env.passwd = SERVERS[env.stage]["password"]
        env.urls = SERVERS[env.stage]["urls"]
        env.docs = SERVERS[env.stage]["docs"]
        env.db_engine = SERVERS[env.stage]["db_engine"]
        env.hosts = [SERVERS[env.stage]["ip_address"], ]
        env.ip = SERVERS[env.stage]["ip_address"]
        env.https = SERVERS[env.stage]["https"]
    else:
        pass


def set_user(superuser=False):
    if superuser:
        env.user, env.password = get_superuser()
    else:
        env.user = make_user(SERVERS[env.stage]["project"])
        env.password = SERVERS[env.stage]["password"]


def isolate_stage(stage):
    if not env.stage == stage:
        raise ValueError('This implementation is only for %s STAGE' % stage.upper())


USERNAME = "vic"
PASSWORD = "haproxy"

class Server(object):

    @staticmethod
    def prepare():
        """
        Install all server dependencies.
        """
        sudo('apt-get update')
        sudo('apt-get upgrade -y')
        sudo('apt-get install -y haproxy')

    @staticmethod
    def haproxy():
        """
        1. Check if haproxy config exist
        2. Delete current haproxy config
        3. Copy the new haproxy config to server
        4. Restart haproxy
        """
        # nginx remove default config
        if exists('/etc/haproxy/haproxy.cfg'):
            sudo('rm /etc/haproxy/haproxy.cfg')

        # Main domain configuration
        with lcd("./tmpl"):
            with cd('/etc/haproxy/'):
                upload_template(
                    filename="./haproxy.cfg",
                    destination='/etc/haproxy/haproxy.cfg',
                    template_dir="./",
                    context={
                        "admin": {"username": USERNAME, "password": PASSWORD},
                        "apps": env.apps,
                        "cluster": env.cluster
                    },
                    use_jinja=True,
                    use_sudo=True,
                )

        sudo('service haproxy restart')
