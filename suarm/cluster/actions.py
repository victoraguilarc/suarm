"""
Script to create and configure a docker swarm cluster over CoreOS in https://www.vultr.com/
"""

import requests, json, sys, os, click
from os.path import isfile
from time import sleep

from fabric.operations import local
from fabric.state import env
from fabric.tasks import execute

from ..errors import valid_int
from .tasks import Cluster
from .vars import OS, ZONES


API_ENDPOINT = "https://api.vultr.com"

CREATE_SERVER = "/v1/server/create"
DESTROY_SERVER = "/v1/server/destroy"
UPGRADE_SERVER = "/v1/server/upgrade_plan"

CREATE_SSHKEY = "/v1/sshkey/create"
DESTROY_SSHKEY = "/v1/sshkey/destroy"
LIST_SSHKEY = "/v1/sshkey/list"
NODE_IPV4 = "/v1/server/list_ipv4"
ENABLE_PRIVATE_NETWORK = "/v1/server/private_network_enable"


CONFIG_FILE = "./swarm.json"
SLEEP_TIME = 5

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
           "email" in settings and \
           "label" in settings:
            return settings
        else:
            sys.exit("""[swarm.json] must be contain the next attributes:
              - api-key
              - ssh-key
              - worker
              - manager
              - email
              - label
            """)
    except Exception as e:
        sys.exit('Valid [swarm.json] file is required!')


def get_headers(settings):
    if "api-key" in settings:
        return {"API-Key": settings["api-key"]}
    return None


def get_cluster_config():
    if isfile(CONFIG_FILE):
        settings = config(CONFIG_FILE)
        headers = get_headers(settings)
    else:
        sys.exit('Valid [swarm.json] file is required!')
    return settings, headers


def register_ip(subid, cluster_exists=False):
    settings, headers = get_cluster_config()
    req = requests.get(API_ENDPOINT + NODE_IPV4, params={"SUBID": subid}, headers=headers)
    if req.status_code == 200:
        ips = req.json()[subid]
        values = {}
        for ip in ips:
            if ip["type"] == "main_ip":
                if ip["ip"] != "0.0.0.0":
                    click.echo("--> Public IP: " + ip["ip"] + " .........  OK.")
                    values["public_ip"] = ip["ip"]

            if ip["type"] == "private" and cluster_exists:
                if ip["ip"] != "0.0.0.0":
                    click.echo("--> Private IP: " + ip["ip"] + " ........  OK.")
                    values["private_ip"] = ip["ip"]
        return values
    else:
        click.echo(req.text)
        return None


def create_server(zone, plan, oss, label, mode="worker"):
    """
    DCID =  Availibilisty region
    VPSPLANID = VPS Plan (Mem/CPU)
    OSID = Operative System
    """
    settings, headers = get_cluster_config()
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
        node = req.json()
        settings[mode]["nodes"].append(node)
        save_on_config(mode, settings[mode])

        click.echo("\n--> Server [%s] created... \n %s" % (mode, req.text))
        return True
    else:
        click.echo("\nERROR >> " + req.text)
        click.echo("--> Couldn't create server, don't forget register a SSH Key")
        return False


def resize_server(subid, plan):
    settings, headers = get_cluster_config()
    payload = {'SUBID': subid, 'VPSPLANID': plan}
    req = requests.post(API_ENDPOINT + UPGRADE_SERVER, data=payload, headers=headers)

    click.echo(req.text)
    if req.status_code == 200:
        click.echo("\n--> Server Upgraded!!")
    else:
        click.echo("\n--> Couldn't update server!!")


def exist_cluster():
    settings, headers = get_cluster_config()
    wk = "nodes" in settings["worker"] and isinstance(settings["worker"]["nodes"], list) \
        and len(settings["worker"]["nodes"]) > 0

    mg = "nodes" in settings["manager"] and isinstance(settings["manager"]["nodes"], list) \
        and len(settings["manager"]["nodes"]) > 0

    return wk and mg


def destroy_server(subid, mode="worker"):
    settings, headers = get_cluster_config()
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
    settings, headers = get_cluster_config()
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


def has_ips(nodes):
    if len(nodes) > 0:
        has = True
        for node in nodes:
            if "public_ip" in node and node["public_ip"] != "0.0.0.0":
                has = has and True
            else:
                has = has and False
        return has
    else:
        return False


def create_servers(replicas, mode="worker"):
    settings, headers = get_cluster_config()
    label = settings["label"]
    zone = settings[mode].get("zone", "NEW_JERSEY")
    plan = settings[mode].get("plan", 201)
    oss = settings[mode].get("os", "COREOS")

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

    if success:
        click.echo("\n---> Registering IP(s)...")
        while True:
            settings, headers = get_cluster_config()
            nodes = settings[mode]["nodes"]

            if len(nodes) > 0:
                for node in nodes:
                    values = register_ip(node["SUBID"])
                    if values:
                        node.update(values)
                        save_on_config(mode, settings[mode])

            if has_ips(nodes):
                break
            else:
                sleep(SLEEP_TIME)
    return success


def create_cluster():
    settings, headers = get_cluster_config()
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
    settings, headers = get_cluster_config()
    local("mkdir -p keys")
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
    settings, headers = get_cluster_config()
    sshkeyid = generate_key(settings["label"])
    if sshkeyid:
        save_on_config("ssh-key", sshkeyid)
    else:
        click.echo("\n--> Invalid or Deleted SSH key")


def destroy_sshkey():
    settings, headers = get_cluster_config()
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
    settings, headers = get_cluster_config()
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


def config_env(continuos_integration=False, cli_deploy=False):
    """
        ENVIRONMENT variables cor CONTINUOS INTEGRATION:
        -----------------------------------------------------
        - CONTINUOS_INTEGRATION (bool): Flag to check CI or not
        - CLUSTER_MASTER (ipv4): This is IP of the Master in the Cluster
        - PROJECT_LABEL (str): It Represents name of the project, it has SLUG format
        - PROJECT_PATH (str): Location to docker-compose installation
        - PROJECT_ENVIRONMENT (variables): This contains [.environment] values
        -----------------------------------------------------
    """
    env.is_ci = continuos_integration
    env.user = 'root'  # default User

    if continuos_integration:
        env.master = os.environ.get('CLUSTER_MASTER', None)
        env.variables = os.environ.get('PROJECT_ENVIRONMENT', None)
        env.path = os.environ.get('PROJECT_PATH', None)
        env.label = os.environ.get('PROJECT_LABEL', None)

        if not env.master or not env.variables or not env.path or not env.label:
            sys.exit("""
             This environment variables are required in CONTINUOS INTEGRATION mode:
                 - CLUSTER_MASTER [%(master)s]
                 - PROJECT_ENVIRONMENT [%(variables)s]
                 - PROJECT_LABEL [%(label)s]
                 - PROJECT_PATH [%(path)s]
            """ % {
                "master": bool(env.master), "variables": bool(env.variables),
                "label": bool(env.label), "path": bool(env.path)
            })
    else:
        if isfile('swarm.json'): # TODO replace swarm.json for dinamic config file

            settings, headers = get_cluster_config()
            env.path = settings["path"] if "path" in settings else "/apps"

            if isfile('keys/%s_rsa' % settings["label"]):
                env.key_filename = 'keys/%s_rsa' % settings["label"]

                # Set WORKER servers
                workers = settings["worker"]["nodes"]
                _workers = []
                for server in workers:
                    _node = dict()
                    if "public_ip" in server:
                        _node["public_ip"] = server["public_ip"]
                    if "private_ip" in server:
                        _node["private_ip"] = server["public_ip"]
                    _workers.append(_node)
                env.workers = _workers

                # Set MANAGER servers
                managers = settings["manager"]["nodes"]
                _managers = []
                for server in managers:
                    _node = dict()
                    if "public_ip" in server:
                        _node["public_ip"] = server["public_ip"]
                    if "private_ip" in server:
                        _node["private_ip"] = server["public_ip"]
                    _managers.append(_node)

                if len(_managers) <= 0:
                    sys.exit('\n-----\n You need configure a cluster MANAGERS first')
                else:
                    env.master = _managers[0]["public_ip"]
                    env.master_private = _managers[0]["private_ip"] if "private_ip" in _managers[0] else None
                    if len(_managers) > 1:
                        _nodes = list(_managers)
                        del _nodes[0]
                        env.managers = _nodes
                    else:
                        env.managers = []

                click.echo("------------------------------------------")
                click.echo("MASTER: %s" % env.master)
                click.echo("MANAGERS: %s" % env.managers)
                click.echo("WORKERS: %s" % env.workers)
                click.echo("------------------------------------------")

            else:
                sys.exit('SSH Key [keys/%s_rsa] file id required \
                to manage cluster.' % settings["label"])

            if cli_deploy and not isfile('.environment'):
                sys.exit("[.environment] file is required for CLI deployment!!")

            if cli_deploy and isfile('.environment'):
                env.label = local("cat .environment | grep PROJECT_LABEL",
                            capture=True).split("=")[1]
                env.registry_host = local("cat .environment | grep REGISTRY_HOST",
                                    capture=True).split("=")[1]
                env.registry_user = local("cat .environment | grep REGISTRY_USER",
                                    capture=True).split("=")[1]

        else:
            sys.exit("""In development MODE [swarm.json] and
            [.environment] files are required!!""")


def setup_cluster():
    config_env()
    settings, headers = get_cluster_config()

    manager = settings["manager"]
    worker = settings["worker"]

    env.manager_os = manager["os"] if "os" in manager else "COREOS"
    env.worker_os = worker["os"] if "os" in worker else "COREOS"
    execute(Cluster.config, hosts=[env.master])
    setup_cluster_dashboard()


def restart_cluster():
    config_env()
    execute(Cluster.restart, hosts=[env.master])
    for manager in env.managers:
        execute(Cluster.restart, hosts=[manager["public_ip"]])
    for worker in env.workers:
        execute(Cluster.restart, hosts=[worker["public_ip"]])


def setup_cluster_as_alpha():
    config_env()
    execute(Cluster.set_alpha_channel, hosts=[env.master])
    for manager in env.managers:
        execute(Cluster.set_alpha_channel, hosts=[manager["public_ip"]])
    for worker in env.workers:
        execute(Cluster.set_alpha_channel, hosts=[worker["public_ip"]])


def show_cluster_docker_version():
    config_env()
    execute(Cluster.docker_version, hosts=[env.master])
    for manager in env.managers:
        execute(Cluster.docker_version, hosts=[manager["public_ip"]])
    for worker in env.workers:
        execute(Cluster.docker_version, hosts=[worker["public_ip"]])


def setup_cluster_registry():
    config_env()
    execute(Cluster.registry, hosts=[env.master])


def setup_cluster_dashboard():
    config_env()
    execute(Cluster.dashboard, hosts=[env.master])


def setup_cluster_proxy():
    config_env()
    execute(Cluster.proxy, hosts=[env.master])


def enable_private_network(mode):
    settings, headers = get_cluster_config()
    for node in settings[mode]["nodes"]:
        payload = {"SUBID": node["SUBID"]}
        req = requests.post(API_ENDPOINT + ENABLE_PRIVATE_NETWORK, data=payload, headers=headers)
        if req.status_code == 200:
            click.echo("\n--> Private network enabled for [%s] server... \n" % node["SUBID"])

        values = register_ip(node["SUBID"], cluster_exists=True)
        if values:
            node.update(values)
            save_on_config(mode, settings[mode])

def setup_cluster_network():

    click.echo("\n ENABLING PRIVATE NETWORK")
    # Enable Private Networks
    enable_private_network("manager")
    enable_private_network("worker")

    # Configure the network interfaces
    click.echo("\n CONFIGURING PRIVATE NETWORK INTERFACES")
    config_env()
    if env.master_private:
        env.private_ip = env.master_private
        execute(Cluster.private_network, hosts=[env.master])

    if env.managers:
        for manager in env.managers:
            env.private_ip = manager["private_ip"]
            execute(Cluster.private_network, hosts=[manager["public_ip"]])

    if env.workers:
        for worker in env.workers:
            env.private_ip = worker["private_ip"]
            execute(Cluster.private_network, hosts=[worker["public_ip"]])
    click.echo("\n PRIVATE NETWORK CONFIGURED ...!!!!")
