import requests, json, sys, os, click
import os.path
from time import sleep

from fabric.state import env
from fabric.tasks import execute
from .tasks import Server, Cluster
from .vars import OS, ZONES
from .errors import *

def add_node(tag, plan=201, oss="COREOS", zone="SILICON_VALLEY"):
    """
      Defaults:
        plan = 1GB RAM / 1CPU
        os = CoreOS
        zone = Silicon Valley
    """
    if exist_cluster():
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
    else:
        click.echo("You need a clouster first")
        return False


def del_node(tag):
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
    if "loadbalancer" in settings and "ipv4" in settings["loadbalancer"]:
        config_env()
        execute(Server.install, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.haproxy, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.letsencrypt, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.restart, hosts=[settings["loadbalancer"]["ipv4"]])
