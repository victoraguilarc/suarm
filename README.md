# ArmCLI

Tools for deploy a cheap Docker Swarm cluster in https://vultr.com servers over CoreOS

## Create Cluster
  - Install build essential tools with `sudo apt install build-essential`
  - Prepare environment with `make env`
  - Configure  `swarm.json` file.
  - Register a ssh key with `arm ssh-keygen`
  - Launch a cluster with `arm create` or `arm -f config_file create`

## Destroy Cluster
  - Destroy cluster with `arm delete` or `arm -f config_file delete`

### Configuration file

By defaul `arm` catch `swarm.json` file as configuration file in the current location
this file, contains the next values to configuration:

```
{
    "api-key": "",
    "ssh-key": "",
    "zone": 0,
    "plan": 0,
    "os": 0,
    "label": "swarm",
    "replicas": 0,
    "cluster": []
}
```
Then
  * **api-key** is obtained from https://my.vultr.com/settings/#settingsapi
  * **ssh-key** is a code for a registered ssh key this is obtained from https://api.vultr.com/v1/sshkey/list
  * **zone** is a availability zone obtained from https://api.vultr.com/v1/regions/list
  * **plan** is a plan (Mem/CPU) obtained from https://api.vultr.com/v1/plans/list
  * **os** is OS id in Vultr obtained from https://api.vultr.com/v1/os/list
  * **label** Is a name for cluster e.g. swarm > swarm01, swarm02 ...
  * **replicas** is the quantity of nodes for cluster
  * **cluster** is the description for nodes in ths cluster


## Swarm configuration

The docker swarm configuration needs a least a node as `manager` and at least two nodes as `workers`

### Register a node manager

`arm` create a ssh keys for cluster during its creation these are located in `keys/` folder. we use them in the next steps.
the ips from nodes are described in `swarm.jsom` after cluster creation.

  - `ssh -i keys/<LABEL>_rsa root@<MASTER_NODE_IP>` acces to the master node.
  - `docker swarm init --advertise-addr <MANAGER-IP>` Start docker as swarm mode.
  - Copy suggested result command to the worker nodes, the command look like as
  ```
  docker swarm join \
    --token SWMTKN-1-49nj1cmql0jkz5s954yi3oex3nedyz0fb0xx14ie39trti4wxv-8vxv8rssmk743ojnwacrr2e7c \
    192.168.99.100:2377
  ```
### Join worker nodes
the worker nodes shoud join to master node with ths suggested command from the last step.

  - `ssh -i keys/<LABEL>_rsa root@<WORKER_NODE_IP>` access to a worker node.
  - Run the last suggested command.
  - Copy suggested result command to the worker nodes, the command look like as
  ```
  docker swarm join \
    --token SWMTKN-1-49nj1cmql0jkz5s954yi3oex3nedyz0fb0xx14ie39trti4wxv-8vxv8rssmk743ojnwacrr2e7c \
    192.168.99.100:2377
  ```

### Tips for nodes

  * Is posible that node are not be in your correct timezone, Fix them with this:
  `sudo timedatectl set-timezone <YOUR_TIME_ZONE> # e.g. America/La_Paz`

## TODOS
  * **scale** command for increase/decrease plan (mem/CPU) of a especific node
  * **increase** command for add more nodes to cluster.









License
-------

This code is licensed under the `MIT License`_.

.. _`MIT License`: https://github.com/vicobits/ArmCLI/blob/master/LICENSE
