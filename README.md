# suarm

Tools for deploy a cheap Docker Swarm cluster in https://vultr.com servers over CoreOS
With a loadbalancer

## Instalation

`[sudo] pip install git+https://github.com/vicobits/ArmCLI.git`

### development
  - Install build essential tools with `sudo apt install build-essential`
  - Prepare environment with `make env`
  - Configure  `swarm.json` file.
  - Edit files

## Usage
  - Add `api-key` to `swarm.json` from value generated in [API Section](https://my.vultr.com/settings/#settingsapi) in
    your [Vultr](https://vultr.com) account.
  - Add some `ssh-key` to  `swarm.json` from your account registered ssh-keys. If you don't have one you can
    create one with `suarm keys --create` and register it with `suarm keys`
  - Create a cluster with `suarm cluster --create` or `suarm -f config_file cluster --create`

## Destroy Cluster
  - Destroy cluster with `suarm cluster --delete` or `suarm -f config_file cluster --delete`

### Configuration file

By defaul `suarm` catch `swarm.json` file as configuration file in the current location
this file, contains the next values:

```
{
    "api-key": "",
    "ssh-key": "",
    "label": "",
    "domain": "cluster.xiberty.com",
    "master": {
        "zone": "SILICON_VALLEY",
        "plan": 201,
        "os": "COREOS",
    },
    "workers": {
        "replicas": 2,
        "zone": "SILICON_VALLEY",
        "plan": 201,
        "os": "COREOS"
    },
    "loadbalancer": {
        "zone": "SILICON_VALLEY",
        "plan": 201,
        "os": "UBUNTU_16_04"
    },
    "cluster": [],
    "apps": [
        {
            "name": "app",
            "domain": "app.xiberty.com",
            "port": "8000",
            "https": false
        }
    ]
}
```
Then
  * **api-key** is obtained from https://my.vultr.com/settings/#settingsapi
  * **ssh-key** is a code for a registered ssh key this is obtained from https://api.vultr.com/v1/sshkey/list
  * **master** is config for master node
  * **loadbalancer** is config for loadbalancer node
  * **workers** is config for workers
  * **cluster** contains the created worker servers details.
  * **label** Is a name for cluster e.g. swarm > swarm01, swarm02 ...
  * **replicas** is the quantity of nodes for cluster it would be greater than 0

  * **zone** is a availability zone obtained from https://api.vultr.com/v1/regions/list
  supported zones are:
  ```
  NEW_JERSEY, CHICAGO, DALLAS, SEATTLE, LOS_ANGELES, ATLANTA,
  AMSTERDAM, LONDON, FRANKFURT, SILICON_VALLEY, SYDNEY,
  PARIS, TOKYO, MIAMI, "SINGAPORE"
  ```
  * **plan** is a plan (Mem/CPU) obtained from https://api.vultr.com/v1/plans/list
  List for common plans are:
  ```
  PLAN     RESOURCES
  ---------------------------------------------------
  201      "1024 MB RAM,25 GB SSD,1.00 TB BW, 1CPU"
  202      "2048 MB RAM,40 GB SSD,2.00 TB BW, 1CPU"
  203      "4096 MB RAM,60 GB SSD,3.00 TB BW, 2CPUs"
  204      "8192 MB RAM,100 GB SSD,4.00 TB BW, 4CPUs"
  205      "16384 MB RAM,200 GB SSD,5.00 TB BW, 6CPUs"
  206      "32768 MB RAM,300 GB SSD,6.00 TB BW, 8CPUs"
  207      "65536 MB RAM,400 GB SSD,10.00 TB BW, 16CPUs"
  208      "98304 MB RAM,800 GB SSD,15.00 TB BW, 24 CPUs",
  ```
  * **os** is OS id in Vultr obtained from https://api.vultr.com/v1/os/list
  List for supported OS are:
  ```
  CENTOS_6, DEBIAN_7, UBUNTU_14_04, COREOS, DEBIAN_8,
  UBUNTU_16_04, FEDORA_25, UBUNTU_17_04, DEBIAN_9, FEDORA_26
  ```

### Register a node manager

`suarm` create a ssh keys for cluster its are located in `keys/` folder. we use them in the next steps.
the ips from nodes are described in `swarm.jsom` after cluster creation.

  - `ssh -i keys/<LABEL>_rsa root@<MASTER_NODE_IP>` to access to the master node.
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

  * Change release channer in CoreOS
  `vim /etc/coreos/update.conf` The content will be `GROUP=alpha`

## Set UI Dashboard for the cluster

One the best dashboards for docker swarm is https://portainer.io/.
By default portainer save the data en `/data` folder and this is cleared when docker is killed/stop or restarted.
we need persist the **portainer** data with these steps.
  - Create folder for volumens in the MASTER NODE with `mkdir -p /volumes/portainer/data`
  - Create a network for portainer `docker network create -d overlay portainer`
  - Start portainer with our new volume:
  ```
  docker service create \
    --name portainer \
    --publish 80:9000 \
    --constraint 'node.role == manager' \
    --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
    --mount type=bind,src=/volumes/portainer/data,dst=/data \
    --network portainer \
    portainer/portainer \
    -H unix:///var/run/docker.sock
  ```
  - Other alternative to portainer is docker swarm visualizer, for run it try:
  ```
  docker service create \
  --name=viz \
  --publish=8080:8080/tcp \
  --constraint=node.role==manager \
  --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  dockersamples/visualizer
  ```

  docker service create \
  --name=nginx-proxy \
  --publish=80:80/tcp \
  --constraint=node.role==manager \
  --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  jwilder/nginx-proxy



 docker run -d -p 80:80 -v /var/run/docker.sock:/tmp/docker.sock:ro jwilder/nginx-proxy

## TODOS
  * **master/slave** automate docker swarm mode in the cluster
  * **manage domains** add doman to the cluster and manage app domains with Cloudflare
  * **deploy app** app deployment with docker-compose

License
-------

This code is licensed under the `MIT License`_.

.. _`MIT License`: https://github.com/vicobits/ArmCLI/blob/master/LICENSE
