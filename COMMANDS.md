# Setup Cluster manually
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
    --publish 9000:9000 \
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
  --publish=8000:8080/tcp \
  --constraint=node.role==manager \
  --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  dockersamples/visualizer
  ```
