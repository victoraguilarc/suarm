"""
Script to create and configure a docker swarm cluster over CoreOS in https://www.vultr.com/
"""

import requests, json, sys, os, click
import os.path
from time import sleep

from fabric.state import env
from fabric.tasks import execute
from .tasks import Server
from .vars import OS, ZONES

API_ENDPOINT = "https://api.vultr.com"

CREATE_SERVER = "/v1/server/create"
DESTROY_SERVER = "/v1/server/destroy"
UPGRADE_SERVER = "/v1/server/upgrade_plan"

CREATE_SSHKEY = "/v1/sshkey/create"
DESTROY_SSHKEY = "/v1/sshkey/destroy"
LIST_SSHKEY = "/v1/sshkey/list"
NODE_IPV4 = "/v1/server/list_ipv4"

CONFIG_FILE = "./swarm.json"
SLEEP_TIME = 15

# SETTINGS
# --------------------
def config(cfile):
    try:
        config_file = open(cfile, 'r')
        settings = json.load(config_file)

        if "api-key" in settings and \
           "ssh-key" in settings and \
           "workers" in settings and \
           "loadbalancer" in settings and \
           "label" in settings:
            return settings
        else:
            sys.exit('\n-----\nA VALID swarm.json file is required!')
            return None
    except Exception as e:
        sys.exit('\n-----\nA VALID swarm.json file is required!')
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
                click.echo("--> IP: " + ip["ip"] + " ...  OK.")
                return ip["ip"]
    else:
        click.echo(req.text)
        return None


settings = config(CONFIG_FILE)
headers = get_headers(settings)


def create_server(zone, plan, oss, label, tag=None):
    """
    DCID =  Availibilisty region
    VPSPLANID = VPS Plan (Mem/CPU)
    OSID = Operative System
    """

    if not tag:
        _nro = len(settings["cluster"])
        if _nro < 10:
            _label = "%s0%s" % (label, _nro)
        else:
            _label = "%s%s" % (label, _nro)
    else:
        _label = label

    _zone = get_zone(zone)
    _os = get_os(oss)

    if not zone or not os:
        click.echo("\nUnsupported OS or ZONE!!")
        return None

    payload = {'DCID': _zone, 'VPSPLANID': plan, 'OSID': _os, 'label': _label, 'host': _label,
               'SSHKEYID': settings["ssh-key"]}
    req = requests.post(API_ENDPOINT + CREATE_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        if tag:
            settings[tag] = req.json()
            settings[tag]["zone"] = zone
            settings[tag]["plan"] = plan
            settings[tag]["os"] = oss
            save_on_config(tag, settings[tag])
            click.echo("\n--> Server [%s] created... \n %s" % (tag, req.text))
        else:
            settings["cluster"].append(req.json())
            save_on_config("cluster", settings["cluster"])
            click.echo("\n--> Server [worker] created... \n" + req.text)
        return True
    else:
        click.echo("\nERROR >> " + req.text)
        click.echo("--> Couldn't create server, don't forget register a SSH Key")
        return False


def destroy_server(subid, srv=None, is_worker=False):
    payload = {'SUBID': subid}
    req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        if srv:
            if "SUBID" in srv:
                srv.pop("SUBID", None)
            if "ipv4" in srv:
                srv.pop("ipv4", None)
        return True
    else:
        click.echo("\n--> Couldn't create server!!")
        return False


def resize_server(subid, plan):
    payload = {'SUBID': subid, 'VPSPLANID': plan}
    req = requests.post(API_ENDPOINT + UPGRADE_SERVER, data=payload, headers=headers)

    click.echo(req.text)
    if req.status_code == 200:
        click.echo("\n--> Server Upgraded!!")
    else:
        click.echo("\n--> Couldn't update server!!")


def exist_cluster():
    return "cluster" in settings and isinstance(settings["cluster"], list) and len(settings["cluster"]) > 0


def destroy_cluster():
    if exist_cluster():
        destroy = input("Destroy Cluster, Are you sure? (y/N) : ")
        if destroy == 'y' or destroy == 'Y':
            success = True
            index = 0

            for node in settings["cluster"]:
                click.echo(node)
                try:
                    subid = int(node["SUBID"])
                    success = success and destroy_server(subid)
                except Exception as e:
                    click.echo("Invalid SUBID: on deleting...")
                    success = False
                index += 1

            if success:
                save_on_config("cluster", list())
            return success and del_node("master") and del_node("loadbalancer")

    else:
        click.echo("\n--> Doesn't exist a cluster created by this script...!!! \n")
        return False

def get_zone(key):
    if key in ZONES:
        return ZONES[key]
    return False


def get_os(key):
    if key in OS:
        return OS[key]
    return False

def create_servers(replicas):
    success = True
    for i in range(replicas):
        success = success and create_server(
            settings["workers"]["zone"], settings["workers"]["plan"],
            settings["workers"]["os"], settings["label"])
        sleep(2)

    if success:
        click.echo("\nRegistering IPs...")

        sleep(SLEEP_TIME)
        for node in settings["cluster"]:
            node["ipv4"] = register_ip(node["SUBID"])
            save_on_config("cluster", settings["cluster"])

        settings["workers"]["replicas"] = len(settings["cluster"])
        save_on_config("workers", settings["workers"])
    return success

def create_cluster():
    if exist_cluster():
        create = input("You have a cluster, Do you want to create another? [Yes/No](Y/N) : ")
        if create == 'n' or create == 'N':
            return None
        elif create != 'y' and create != 'Y':
            return None
    else:
        settings["cluster"] = []
        save_on_config("cluster", list())

    if len(settings["ssh-key"]) > 0:

        if "replicas" in settings["workers"] and \
            isinstance(settings["workers"]["replicas"], int) and \
            settings["workers"]["replicas"] > 0:

            success = create_servers(settings["workers"]["replicas"]) and \
                      add_node("master") and add_node("loadbalancer", oss="UBUNTU_16_04")

            if success:
                click.echo("\n-----------------------------------------------------------------------------------'")
                click.echo("Cluster created, don't forget save ssh keys, its are in './keys'")
                click.echo("-----------------------------------------------------------------------------------'")

            return success
        else:
            click.echo("\nInvalid value in [workers][replicas] \nThis must be an integer greater than 0\n")
            return False
    else:
        click.echo("\n--> Would be register a SSH Key first with: 'make cluster_keygen'")
        return False


def generate_key(label):
    os.system("ssh-keygen -t rsa -b 4096 -C '%(label)s cluster' -f ./keys/%(label)s_rsa -N ''" % {"label": label})
    f = open("./keys/%s_rsa.pub" % label, "r")
    ssh_key = f.readline()
    f.close()
    click.echo(ssh_key)
    payload = {'name': '%s Cluster Key' % label, 'ssh_key': ssh_key}
    req = requests.post(API_ENDPOINT + CREATE_SSHKEY, data=payload, headers=headers)

    if req.status_code == 200:
        click.echo("\n--> SSH Key Registered..." + req.text)
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
            click.echo("\n--> ERROR: %s " % req.text)
    else:
        click.echo("\n--> Invalid SSH key")

def list_sshkeys():
    req = requests.get(API_ENDPOINT + LIST_SSHKEY, headers=headers)
    if req.status_code == 200:
        _keys = req.json()
        if len(_keys) > 0:
            click.echo("Your keys on vultr\n-----------------------------------")
            index = 0
            _for_select = []
            for key in _keys.values():
                click.echo("%s. [%s]: %s" % (index+1, key["name"], key["SSHKEYID"]))
                _for_select.append(key)
                index += 1

            create = input("\nDo you wish register any key in your config? [Yes/No](Y/N): ")
            if create == 'y' or create == 'Y':
                reg = input("Put your key number [1/2/3...]: ")
                try:
                    _reg = int(reg)
                    # import ipdb; ipdb.set_trace()
                    if 0 < _reg <= len(_for_select):
                        save_on_config("ssh-key", _for_select[_reg-1]["SSHKEYID"])
                        click.echo("Ready!!!")
                    else:
                        click.echo("The value must be between the options in the list")
                except Exception as e:
                    click.echo("Invalid value...")



    else:
        click.echo("\n--> ERROR: %s " % req.text)


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
        execute(Server.letsencrypt, hosts=[settings["loadbalancer"]["ipv4"]])
        execute(Server.restart, hosts=[settings["loadbalancer"]["ipv4"]])
