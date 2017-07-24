"""
Script to create and configure a docker swarm cluster over CoreOS in https://www.vultr.com/
"""

import requests, json, sys, os, click
import os.path
from time import sleep

from fabric.state import env
from fabric.tasks import execute
from .tasks import Server

API_ENDPOINT = "https://api.vultr.com"
CREATE_SERVER = "/v1/server/create"
DESTROY_SERVER = "/v1/server/destroy"
CREATE_SSHKEY = "/v1/sshkey/create"
DESTROY_SSHKEY = "/v1/sshkey/destroy"
NODE_IPV4 = "/v1/server/list_ipv4"

CONFIG_FILE = "./swarm.json"
SLEEP_TIME = 15

# SETTINGS
# --------------------


def config(cfile):
    os.system("ls")
    try:
        config_file = open(cfile, 'r')
        settings = json.load(config_file)
        if "api-key" in settings and \
           "ssh-key" in settings and \
           "nodes" in settings and \
           "label" in settings and \
           "zone" in settings["nodes"] and \
           "plan" in settings["nodes"] and \
           "os" in settings["nodes"] and \
           "replicas" in settings["nodes"]:

            click.echo("\n--> Valid config file...")
            return settings
        else:
            click.echo("\n---> 'swarm.json' hasn't a valid format")
            return None
    except Exception as e:
        click.echo(e)
        click.echo('swarm.json VALID file is required!')
        return None


def get_headers(settings):
    if "api-key" in settings:
        return {"API-Key": settings["api-key"]}
    return None


def register_ip(subid):
    req = requests.get(API_ENDPOINT + NODE_IPV4, params={"SUBID": subid}, headers=headers)
    if req.status_code == 200:
        ips = req.json()[subid]
        for ip in ips:
            if ip["type"] == "main_ip":
                click.echo("--> IP: " + ip["ip"] + " Registered...")
                return ip["ip"]
    else:
        click.echo(req.text)
        return None


settings = config(CONFIG_FILE)
headers = get_headers(settings)


def create_server(zone, plan, oss, label, is_lb=False):
    """
    DCID =  Availibility region
    VPSPLANID = VPS Plan (Mem/CPU)
    OSID = Operative System
    """

    payload = {'DCID': zone, 'VPSPLANID': plan, 'OSID': oss, 'label': label, 'host': label,
               'SSHKEYID': settings["ssh-key"]}
    req = requests.post(API_ENDPOINT + CREATE_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        if is_lb:
            settings["loadbalancer"] = req.json()
            settings["loadbalancer"]["zone"] = zone
            settings["loadbalancer"]["plan"] = plan
            settings["loadbalancer"]["os"] = oss

            save_on_config("loadbalancer", settings["loadbalancer"])
            click.echo("\n--> Load Balancer created... \n" + req.text)
        else:
            settings["cluster"].append(req.json())
            save_on_config("cluster", settings["cluster"])
            click.echo("--> Server created..." + req.text)
    else:
        click.echo("\nERROR >> " + req.text)
        click.echo("\n--> Couldn't create server, don't forget register a SSH Key")


def destroy_server(subid):
    payload = {'SUBID': subid}
    req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        click.echo("\n--> Server deleted!!")
    else:
        click.echo("\n--> Couldn't create server!!")


def exist_cluster():
    return "cluster" in settings and isinstance(settings["cluster"], list) and len(settings["cluster"]) > 0


def destroy_cluster():
    if exist_cluster():
        destroy = input("Destroy Cluster, Are you sure? (y/N) : ")
        if destroy == 'y' or destroy == 'Y':
            destroy_sshkey()
            success = True
            for node in settings["cluster"]:
                click.echo(node)
                try:
                    subid = int(node["SUBID"])
                    destroy_server(subid)
                except Exception as e:
                    click.echo("Invalid SUBID: on deleting...")
                    success = False
            if success:
                save_on_config("cluster", list())
                destroy_loadbalancer()
    else:
        click.echo("\n--> Doesn't exist a cluster created by this script...!!! \n")


def create_servers(replicas):
    for i in range(replicas):
        create_server(
            settings["nodes"]["zone"], settings["nodes"]["plan"],
            settings["nodes"]["os"], "%s0%s" % (settings["label"], i))
        sleep(2)

    click.echo("\nRegistering IPs...")

    sleep(SLEEP_TIME)
    for node in settings["cluster"]:
        node["ipv4"] = register_ip(node["SUBID"])
        save_on_config("cluster", settings["cluster"])

    if "nodes" in settings and "replicas" in settings["nodes"]:
        settings["nodes"]["replicas"] = len(settings["cluster"])
        save_on_config("nodes", settings["nodes"])


def create_cluster():
    if exist_cluster():
        create = input("You have a Cluster, Do you want to reset it? [Yes/No/Cancel](Y/N/C) : ")
        if create == 'c' or create == 'C':
            click.echo("\n----> You are wise!")
            return None
        elif create == 'y' or create == 'Y':
            settings["cluster"] = []
            save_on_config("cluster", list())
    else:
        settings["cluster"] = []
        save_on_config("cluster", list())

    if len(settings["ssh-key"]) > 0:

        if isinstance(settings["nodes"]["replicas"], int):

            create_servers(settings["nodes"]["replicas"])
            add_loadbalancer()

            click.echo("\n\n-----------------------------------------------------------------------------------'")
            click.echo("Cluster created, don't forget save ssh keys, its are in './keys'")
            click.echo("-----------------------------------------------------------------------------------'")
    else:
        click.echo("\n--> Would be register a SSH Key first with: 'make cluster_keygen'")


def generate_key(label):
    os.system("ssh-keygen -t rsa -b 4096 -C '%(label)s cluster' -f ./keys/%(label)s_rsa -N ''" % {"label": label})
    f = open("./keys/%s_rsa.pub" % label, "r")
    ssh_key = f.readline()
    f.close()
    click.echo(ssh_key)
    payload = {'name': '%s Cluster Key' % label, 'ssh_key': ssh_key}
    req = requests.post(API_ENDPOINT + CREATE_SSHKEY, data=payload, headers=headers)

    if req.status_code == 200:
        click.echo("\n--> SSH Key registered..." + req.text)
        return req.json()["SSHKEYID"]
    return None


def save_on_config(key, value):
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        data[key] = value

    os.remove(CONFIG_FILE)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def register_sshkey():
    sshkeyid = generate_key(settings["label"])
    if sshkeyid:
        save_on_config("ssh-key", sshkeyid)
    else:
        click.echo("\n--> Invalid or Deleted SSH key")


def destroy_sshkey():
    sshkeyid = settings["ssh-key"]
    if sshkeyid:
        payload = {'SSHKEYID': sshkeyid}
        req = requests.post(API_ENDPOINT + DESTROY_SSHKEY, data=payload, headers=headers)
        if req.status_code == 200:
            save_on_config("ssh-key", "")
            try:
                os.remove("./keys/%s_rsa" % settings["label"])
                os.remove("./keys/%s_rsa.pub" % settings["label"])
            except Exception as e:
                pass
            click.echo("\n--> SSH Key Destroyed...")
    else:
        click.echo("\n--> Invalid SSH key")


def add_loadbalancer(plan=201, oss=215, zone=12):
    """
        plan = 1GB RAM / 1CPU
        os = ubuntu 16.04
    """

    if exist_cluster():
        if "loadbalancer" in settings:
            if "SUBID" in settings["loadbalancer"] and "ipv4" in settings["loadbalancer"]:
                create = input("Are your sure to (re)create this? (y/N) : ")
                if create != 'y' and create != 'Y':
                    click.echo("\n----> You are wise!")
                    return None

            if "zone" in settings["loadbalancer"]:
                zone = settings["loadbalancer"]["zone"]

            if "plan" in settings["loadbalancer"]:
                plan = settings["loadbalancer"]["plan"]

            if "os" in settings["loadbalancer"]:
                oss = settings["loadbalancer"]["os"]

        else:
            settings["loadbalancer"] = dict()
            zone = settings["zone"]

        create_server(zone=zone, plan=plan, oss=oss, label="%s-lb" % settings["label"], is_lb=True)
        if "SUBID" in settings["loadbalancer"]:
            sleep(SLEEP_TIME)
            settings["loadbalancer"]["ipv4"] = register_ip(settings["loadbalancer"]["SUBID"])
            save_on_config("loadbalancer", settings["loadbalancer"])
    else:
        click.echo("You need a clouster first")


def config_env():
    env.user = 'root'
    env.key_filename = 'keys/%s_rsa' % settings["label"]
    env.apps = settings["apps"]
    env.cluster = settings["cluster"]


def setup_loadbalancer():
    if "loadbalancer" in settings and "ipv4" in settings["loadbalancer"]:
        config_env()
        execute(Server.install, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.haproxy, hosts=[settings["loadbalancer"]["ipv4"]])


def destroy_loadbalancer():
    if "loadbalancer" in settings and "SUBID" in settings["loadbalancer"]:
        payload = {'SUBID': settings["loadbalancer"]["SUBID"]}
        req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
        if req.status_code == 200:
            settings["loadbalancer"] = {
                "zone": 12,
                "plan": 201,
                "os": 215,
            }
            save_on_config("loadbalancer", settings["loadbalancer"])
            click.echo("\n--> Server deleted!!")
        else:
            click.echo("\n--> Couldn't create server!!")
    else:
        click.echo("\n--> Load Balancer improperly configured!!")