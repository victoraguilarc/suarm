.PHONY: env
.SILENT:

COMPOSE := docker-compose -f dev.yml

# Variables
PIP := ./env/bin/pip
PYTHON := ./env/bin/python

# CONFIGURATION
env:
	virtualenv -p python3 env --always-copy --no-site-packages
	$(PIP) install pip --upgrade
	$(PIP) install setuptools --upgrade
	$(PIP) install -r requirements.txt
	. env/bin/activate
	$(PIP) install --editable .

# CREATE CLUSTER
create_cluster:
	$(PYTHON) ./tools/swarm/cluster.py create

# DESTROY CLUSTER
destroy_cluster:
	$(PYTHON) ./tools/swarm/cluster.py destroy

# SUPPLY CLUSTER
cluster_keygen:
	$(PYTHON) ./tools/swarm/cluster.py ssh-keygen
