# suarm

Tools for deploy a cheap Docker Swarm cluster in https://vultr.com servers over CoreOS
With a loadbalancer

## Installation

`[sudo] pip install git+https://github.com/vicobits/suarm.git`

#### development
  - Install build essential tools with `sudo apt install build-essential`
  - Prepare environment with `make env`
  - Configure  `swarm.json` file.
  - Edit files

## Usage

#### Create Cluster
  - Add `api-key` to `swarm.json` from value generated in [API Section](https://my.vultr.com/settings/#settingsapi) in
    your [Vultr](https://vultr.com) account.
  - Generate a ssh-key for your project with the command `suarm keys --create`.
  - Register your generated ssh-key into `swarm.json` file with selecting between your registered keys with `suarm keys`
  - Create a cluster with `suarm cluster --create` or `suarm -f <config_file> cluster --create`

#### Destroy Cluster
  - Destroy cluster with `suarm cluster --delete` or `suarm -f <config_file> cluster --delete`

### Configuration file

By defaul `suarm` catch `swarm.json` file as configuration file in the current location
this file, contains the next values:

```
{
    "api-key": "<MY_VULTR_API_KEY>",
    "ssh-key": "<MY_VULTR_GENERATED_SSHKEYID>",
    "label": "<NAME_FOR_SWARM>",
    "domain": "<DOMAIN_FOR_SWARM_MASTER>",
    "email": "<YOUR_EMAIL>",
    "manager": {
        "replicas": 1,
        "zone": "NEW_JERSEY",
        "plan": 201,
        "os": "COREOS",
        "nodes": []
    },
    "worker": {
        "replicas": 2,
        "zone": "NEW_JERSEY",
        "plan": 201,
        "os": "COREOS",
        "nodes": []
    },
    "apps": [
        {
            "name": "web",
            "domain": "app1.example.com",
            "port": 30000,
            "https": true
        }
    ]
}
```
Where
  * **api-key** is obtained from the [api](https://my.vultr.com/settings/#settingsapi)
  * **ssh-key** is a SSHKEYID of some your registered ssh keys in the server this is obtained from [api](https://api.vultr.com/v1/sshkey/list)
  * **manager** is config for manager nodes
  * **worker** is config for worker nodes
  * **label** Is a name for cluster e.g. swarm > swarm-manager, swarm-worker00, swarm-worker01, ...
  * **replicas** is the quantity of nodes
  * **zone** is a availability zone obtained from the [api](https://api.vultr.com/v1/regions/list)
  supported zones are:
  ```
  NEW_JERSEY      CHICAGO           DALLAS          SILICON_VALLEY
  SEATTLE         LOS_ANGELES       ATLANTA         SYDNEY
  AMSTERDAM       LONDON            FRANKFURT       SINGAPORE
  PARIS           TOKYO             MIAMI
  ```
  * **plan** representa resources for server (Mem/CPU/Price), obtained from the [api](https://api.vultr.com/v1/plans/list)
  List for common plans are:
  ```
  PLAN     MEMORY RAM        STORAGE        BANDWIDTH       CPU         PRICE
  -------------------------------------------------------------------------------
  201      1024 MB RAM      25 GB SSD       1.00 TB BW      1CPU        5 USD
  202      2048 MB RAM      40 GB SSD       2.00 TB BW      1CPU        10 USD
  203      4096 MB RAM      60 GB SSD       3.00 TB BW      2CPUs       20 USD
  204      8192 MB RAM      100 GB SSD      4.00 TB BW      4CPUs       40 USD
  205      16384 MB RAM     200 GB SSD      5.00 TB BW      6CPUs       80 USD
  206      32768 MB RAM     300 GB SSD      6.00 TB BW      8CPUs       160 USD
  207      65536 MB RAM     400 GB SSD      10.00 TB BW     16CPUs      320 USD
  208      98304 MB RAM     800 GB SSD      15.00 TB BW     24 CPUs     640 USD
  ```
  * **os** is OS id in Vultr obtained from the [API](https://api.vultr.com/v1/os/list)
  List for supported OS are:
  ```
  CENTOS_6        DEBIAN_7      UBUNTU_14_04      COREOS      DEBIAN_8,
  UBUNTU_16_04    FEDORA_25     UBUNTU_17_04      DEBIAN_9    FEDORA_26
  ```
# Configure cluster

#### Setup swarm
Use the command `suarm cluster --setup` to configure manager and worker nodes.

#### Setup dashboard
Use the command `suarm cluster --setup-dashboard` to install [portainer](https://portainer.io/) and [vizualizer](https://github.com/dockersamples/docker-swarm-visualizer).

#### Setup proxy
Use the command `suarm cluster --setup-proxy` to install proxy flow base on [DockerFlow](http://dockerflow.com).

## Setup cluster manually
For setup cluster manually check [Manually docs](COMMANDS.md)


## TODOS
  * **manage domains** add domain to the cluster and manage app domains with Cloudflare
  * **deploy app** app deployment with docker-compose

## Extra Config
For proxy config options check [dockerflow-proxy](http://proxy.dockerflow.com)
For letsencrypt config options check [dockerflow-le](https://github.com/n1b0r/docker-flow-proxy-letsencrypt)

License
-------
This code is licensed under the `MIT License`_.

.. _`MIT License`: https://github.com/vicobits/suarm/blob/master/LICENSE
