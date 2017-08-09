

import json
from getpass import getpass

import sys

import os
from fabric.operations import local, prompt
from fabric.state import env


# ~$ PATH - CONFIGURATION
# ---------------------------------------------------------------------

CONFIG_FILE = "django.json"
HOME_PATH = "/webapps"

DB_MYSQL = "mysql"
DB_POSTGRESQL = "postgres"

WS_NGINX = "nginx"
WS_APACHE = "apache"


def config(cfile=CONFIG_FILE):
    try:
        config_file = open(cfile, 'r')
        return json.load(config_file)
    except Exception as e:
        print(e)
        sys.exit('Valid [django.json] file is required!')

servers = config()


def get_value(stage, key, default=None):
    if key in servers[stage]:
        return servers[stage][key]
    elif default:
        return default
    else:
        sys.exit('[%s] value in needed in [%s] server' % (key, stage))


def make_user(project):
    return "%s_user" % project


def make_team(project):
    return "%s_team" % project


def make_app(project):
    return "%s_app" % project


def get_user_home(stage="develop"):
    return "%(home_path)s/%(user)s" % {
        "home_path": HOME_PATH,
        "user": make_user(servers[stage]["project"]),
    }


def get_project_path(stage="develop"):
    return "%(user_home)s/%(project)s" % {
        "user_home": get_user_home(stage),
        "project": make_app(servers[stage]["project"]),
    }


def get_project_src(stage="develop"):
    return "%(user_home)s/%(project)s/src" % {
        "user_home": get_user_home(stage),
        "project": make_app(servers[stage]["project"]),
    }


def has_key(stage, key):
    return key in servers[stage]


def set_stage(stage='production'):
    if stage in servers.keys():
        env.stage = stage
        env.project = get_value(env.stage, "project")
        env.domain = get_value(env.stage, "domain")
        env.passwd = get_value(env.stage, "password", default="11002299338844775566")
        env.urls = get_value(env.stage, "urls")
        env.db_engine = get_value(env.stage, "db_engine", default=DB_POSTGRESQL)
        env.hosts = [get_value(env.stage, "ipv4")]
        env.web_server = get_value(env.stage, "web_server", default=WS_NGINX)
        env.ipv4 = get_value(env.stage, "ipv4")
        env.https = get_value(env.stage, "https", default=True)
        if env.https and not has_key(env.stage, "email"):
            sys.exit('\n\n[https] activated for [%s] server, [email] value is needed to continue...\n' % stage)
        else:
            env.email = get_value(env.stage, "email")

    else:
        sys.exit("[%s] server doesn't registered into config file" % stage)


def set_user(superuser=False):
    if superuser:
        env.user = username = get_value(env.stage, "superuser", default="root")
        if has_key(env.stage, "key_filename") and os.path.isfile(get_value(env.stage, "key_filename", default=None)):
            env.key_filename = servers[env.stage]["key_filename"]
        else:
            env.password = getpass("Put password for [%s]: " % username)
            if len(env.password) == 0:
                sys.exit("[superuser] password is needed to make server configurations")
    else:
        env.user = make_user(servers[env.stage]["project"])
        env.password = servers[env.stage]["password"]


def isolate_stage(stage):
    if not env.stage == stage:
        raise ValueError('This implementation is only for %s STAGE' % stage.upper())


