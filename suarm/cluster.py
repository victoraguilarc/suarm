"""
Script to create and configure a docker swarm cluster over CoreOS in https://www.vultr.com/
"""

import requests, json, sys, os, click
import os.path
from time import sleep

from fabric.state import env
from fabric.tasks import execute
from .tasks import Server, Cluster
from .vars import OS, ZONES
from .errors import *


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
           "worker" in settings and \
           "manager" in settings and \
           "apps" in settings and \
           "email" in settings and \
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


def create_server(zone, plan, oss, label, mode="worker"):
    """
    DCID =  Availibilisty region
    VPSPLANID = VPS Plan (Mem/CPU)
    OSID = Operative System
    """
    _zone = get_zone(zone)
    _oss = get_os(oss)

    if not _zone:
        click.echo("\nUnsupported ZONE, we use default ZONE!!")
        _zone = "NEW_JERSEY"

    if not _oss:
        click.echo("\nUnsupported OS, we use default OS!!")
        _oss = "COREOS"

    payload = {'DCID': _zone, 'VPSPLANID': plan, 'OSID': _oss, 'label': label, 'host': label,
               'SSHKEYID': settings["ssh-key"]}

    req = requests.post(API_ENDPOINT + CREATE_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        settings[mode]["nodes"].append(req.json())
        save_on_config(mode, settings[mode])
        click.echo("\n--> Server [%s] created... \n %s" % (mode, req.text))
        return True
    else:
        click.echo("\nERROR >> " + req.text)
        click.echo("--> Couldn't create server, don't forget register a SSH Key")
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
    wk = "nodes" in settings["worker"] and isinstance(settings["worker"]["nodes"], list) \
        and len(settings["worker"]["nodes"]) > 0

    mg = "nodes" in settings["manager"] and isinstance(settings["manager"]["nodes"], list) \
        and len(settings["manager"]["nodes"]) > 0

    return wk and mg


def destroy_server(subid, mode="worker"):
    payload = {'SUBID': subid}
    req = requests.post(API_ENDPOINT + DESTROY_SERVER, data=payload, headers=headers)
    if req.status_code == 200:
        nodes = settings[mode]["nodes"]
        _nodes = []
        for node in nodes:
            if "SUBID" in node and node["SUBID"] != subid:
                _nodes.append(node)

        settings[mode]["nodes"] = _nodes
        save_on_config(mode, settings[mode])
        return True
    else:
        click.echo("\n--> Couldn't create server!!, ERROR: %s" % req.text)
        return False


def destroy_servers(mode="worker"):
    nodes = settings[mode]["nodes"]
    success = True; index = 0
    for node in nodes:
        click.echo(node)
        try:
            subid = node["SUBID"]
            success = success and destroy_server(subid, mode=mode)
        except Exception as e:
            click.echo("Invalid SUBID: on deleting...")
            success = success and False
        index += 1

    if success:
        click.echo("The [%s] servers destroyed!!" % mode)
        settings[mode]["nodes"] = list()
        save_on_config(mode, settings[mode])
    return success


def destroy_cluster():
    if exist_cluster():
        destroy = input("Destroy Cluster, Are you sure? (y/N) : ")
        if destroy == 'y' or destroy == 'Y':
            return destroy_servers(mode="worker") and destroy_servers(mode="manager")
        else:
            return False
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


def create_servers(replicas, mode="worker"):

    label = settings["label"]
    zone = settings[mode].get("zone", "NEW_JERSEY")
    plan = settings[mode].get("plan", 201)
    oss = settings[mode].get("os", "COREOS")
    nro = len(settings[mode]["nodes"])

    if replicas <= 0:
        sys.exit("You need at least 1 replica")

    success = True
    for nro in range(replicas):

        if len(range(replicas)) == 1:
            _label = "%s-%s" % (label, mode)
        elif nro < 10:
            _label = "%s-%s0%s" % (label, mode, nro)
        else:
            _label = "%s-%s%s" % (label, mode, nro)

        success = success and create_server(zone, plan, oss, _label, mode=mode)
        sleep(2)

    if success:
        click.echo("\nRegistering IPs...")
        sleep(SLEEP_TIME)

        for node in settings[mode]["nodes"]:
            node["ipv4"] = register_ip(node["SUBID"])
            save_on_config(mode, settings[mode])

        settings[mode]["replicas"] = len(settings[mode]["nodes"])
        save_on_config(mode, settings[mode])
    return success


def create_cluster():
    if exist_cluster():
        create = input("You have a cluster, Do you want to create another? [Yes/No](Y/N) : ")
        if create == 'n' or create == 'N':
            return None
        elif create != 'y' and create != 'Y':
            return None
    else:
        settings["worker"]["nodes"] = []
        settings["manager"]["nodes"] = []
        save_on_config("worker", settings["worker"])
        save_on_config("manager", settings["manager"])


    if len(settings["ssh-key"]) > 0:

        # Create worker nodes
        worker_replicas = settings["worker"].get("replicas", 1)
        manager_replicas = settings["manager"].get("replicas", 1)

        if valid_int(worker_replicas) and valid_int(manager_replicas):

            success = create_servers(worker_replicas, mode="worker") and \
                      create_servers(manager_replicas, mode="manager")

            if success:
                click.echo("\n-----------------------------------------------------------------------------------")
                click.echo(" Cluster created, don't forget save ssh keys, its are in './keys'")
                click.echo("-----------------------------------------------------------------------------------")
        else:
            click.echo("\nInvalid value in [workers][replicas] \nThis must be an integer greater than 0\n")
    else:
        click.echo("\n--> Would be register a SSH Key first with: 'suarm keys --create'")
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

def setup_workers():
    nodes = env.nodes

    if len(nodes) == 0:
        sys.exit('\n-----\n You need configure a cluster WORKERS first')

    index = 0
    for node in nodes:
        env.ipv4 = node["ipv4"]
        execute(Cluster.worker, hosts=[env.ipv4])


def setup_managers():
    nodes = env.nodes

    if len(nodes) == 0:
        sys.exit('\n-----\n You need configure a cluster MANAGERS first')

    if len(nodes) == 1:
        env.ipv4 = nodes[0]["ipv4"]
        execute(Cluster.manager_primary, hosts=[env.ipv4])
    else:
        index = 0
        for node in nodes:
            env.ipv4 = node["ipv4"]
            if index == 0:
                execute(Cluster.manager_primary, hosts=[env.ipv4])
            else:
                execute(Cluster.manager_secondary, hosts=[env.ipv4])
            index += 1

def config_env():
    env.user = 'root'
    env.key_filename = 'keys/%s_rsa' % settings["label"]
    env.apps = settings["apps"]


    workers = settings["worker"]["nodes"]
    _workers = []
    for server in workers:
        _workers.append(server["ipv4"])
    env.workers = _workers

    managers = settings["manager"]["nodes"]
    _managers = []
    for server in managers:
        _managers.append(server["ipv4"])

    if len(_managers) <= 0:
        sys.exit('\n-----\n You need configure a cluster MANAGERS first')
    else:
        env.master = _managers[0]
        if len(_managers) > 1:
            _nodes = list(_managers)
            del _nodes[0]
            env.managers = _nodes
        else:
            env.managers = None

    click.echo("------------------------------------------")
    click.echo("MASTER: %s" % env.master)
    click.echo("MANAGERS: %s" % env.managers)
    click.echo("WORKERS: %s" % env.workers)
    click.echo("------------------------------------------")


def setup_cluster():
    config_env()
    execute(Cluster.config, hosts=[env.master])
    xetup_dashboard()
    # sed -i -e 's/stable/alpha/g' hello.txt
    # update_engine_client -update


def xetup_registry():
    config_env()
    execute(Cluster.registry, hosts=[env.master])


def xetup_dashboard():
    config_env()
    execute(Cluster.dashboard, hosts=[env.master])


def xetup_proxy():
    config_env()
    execute(Cluster.proxy, hosts=[env.master])
