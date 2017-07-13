
"""
Script to create and configure a docker swarm cluster over CoreOS in https://www.vultr.com/
"""

import requests, json, sys, os, click
import os.path
from time import sleep

API_ENDPOINT = "https://api.vultr.com"
CREATE_SERVER = "/v1/server/create"
DESTROY_SERVER = "/v1/server/destroy"
CREATE_SSHKEY = "/v1/sshkey/create"
DESTROY_SSHKEY = "/v1/sshkey/destroy"
NODE_IPV4 = "/v1/server/list_ipv4"

CONFIG_FILE = "./swarm.json"
CACHE_FILE = "./cluster.lst"

# settingsURATION
# --------------------
def config(cfile):
    os.system("ls")
    try:
        config_file = open(cfile, 'r')
        settings = json.load(config_file)
        if "api-key" in settings and "ssh-key" in settings and "zone" in settings and "plan" in settings and \
           "os" in settings and "label" in settings and "replicas" in settings:
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

settings = config(CONFIG_FILE)
headers = get_headers(settings)


def create_server(zone, plan, os, label, is_lb=False):
    """
    DCID =  Availibility region
    VPSPLANID = VPS Plan (Mem/CPU)
    OSID = Operative System
    """

    payload = {'DCID': zone, 'VPSPLANID': plan, 'OSID': os, 'label': label, 'host': label, 'SSHKEYID': settings["ssh-key"]}
    req = requests.post(API_ENDPOINT + CREATE_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        if is_lb:
            settings["loadbalancer"] = req.json()
            replace_config_key("loadbalancer", settings["loadbalancer"])
            click.echo("\n--> Load Balancer created..." + req.text)
        else:
            settings["cluster"].append(req.json())
            replace_config_key("cluster", settings["cluster"])
            click.echo("\n--> Server created..." + req.text)
    else:
        click.echo("\n--> Couldn't create server, don't forget register a SSH Key")


def destroy_server(subid):
    payload = {'SUBID': subid}
    req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        click.echo("\n--> Server deleted!!")
    else:
        click.echo("\n--> Couldn't create server!!")

def exist_cluster():
    return ("cluster" in settings and isinstance(settings["cluster"], list) \
        and len(settings["cluster"]) > 0)

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
                    click.echo("Invalid SUBID: [" + subid + "] on deleting...")
                    success = False
            if success:
                replace_config_key("cluster", list())
    else:
        click.echo("\n--> Doesn't exist a cluster created by this script...!!! \n")



def create_cluster():
    if exist_cluster():
        create = input("You have a Cluster, Are your sure to create one more? (y/N) : ")
        if create != 'y' and create != 'Y':
            click.echo("\n----> You are wise!")
            return None
    else:
        settings["cluster"] = []
        replace_config_key("cluster", list())

    if len(settings["ssh-key"]) > 0:
        if isinstance(settings["replicas"], int):
            for i in range(settings["replicas"]):
                create_server(
                    settings["zone"], settings["plan"],
                    settings["os"], "%s0%s" % (settings["label"], i))

            sleep(5)
            click.echo("Registering IPs...")
            if exist_cluster():
                for node in settings["cluster"]:

                    req = requests.get(API_ENDPOINT + NODE_IPV4, params={"SUBID": node["SUBID"]}, headers=headers)
                    if req.status_code == 200:
                        ips = req.json()[node["SUBID"]]
                        for ip in ips:
                            if ip["type"] == "main_ip":
                                node["ipv4"] = ip["ip"]
                                replace_config_key("cluster", settings["cluster"])
                    else:
                        click.echo(req.text)
                    #
                    # v1/server/list_ipv4?SUBID=9470440

            click.echo("\n-----------------------------------------------------------------------------------'")
            click.echo("\n Cluster created, don't forget save ssh keys, its are in './keys'")
            click.echo("\n-----------------------------------------------------------------------------------'")
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

def replace_config_key(key, value):
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        data[key] = value

    os.remove(CONFIG_FILE)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def register_sshkey():
    sshkeyid = generate_key(settings["label"])
    if sshkeyid:
        replace_config_key("ssh-key", sshkeyid)
    else:
        click.echo("\n--> Invalid or Deleted SSH key")

def destroy_sshkey():
    sshkeyid = settings["ssh-key"]
    if sshkeyid:
        payload = {'SSHKEYID': sshkeyid}
        req = requests.post(API_ENDPOINT + DESTROY_SSHKEY, data=payload, headers=headers)
        if req.status_code == 200:
            replace_config_key("ssh-key", "")
            try:
                os.remove("./keys/%s_rsa" % settings["label"])
                os.remove("./keys/%s_rsa.pub" % settings["label"])
            except Exception as e:
                pass
            click.echo("\n--> SSH Key Destroyed...")
    else:
        click.echo("\n--> Invalid SSH key")

def add_loadbalancer():
    DEFAULT_LB_PLAN = 201 # 1GB RAM / 1CPU
    DEFAULT_LB_OS = 215 # ubuntu 16.04
    if exist_cluster():
        if not "loadbalancer" in settings:
            settings["loadbalancer"] = dict()

        create_server(["zone"], DEFAULT_LB_PLAN,
            DEFAULT_LB_OS, "%s-lb" % settings["label"], is_lb=True)

    else:
        click.echo("You need a clouster first")
