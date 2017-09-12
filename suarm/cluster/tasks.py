from __future__ import unicode_literals

import os, sys, re, click
from getpass import getpass
from os.path import isfile

from fabric.context_managers import cd, quiet, hide
from fabric.contrib.files import exists, upload_template
from fabric.operations import run, local
from fabric.state import env
from fabric.api import settings
from fabric.tasks import execute
from pkg_resources import resource_filename, Requirement


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Cluster(object):

    @staticmethod
    def private_network():
        # with settings(warn_only=True):

        if env.os == "COREOS":

            run("echo \"%s%s%s\" > /etc/systemd/network/static.network" %
            (
                "[Match]\nName=eth1\n",
                "[Link]\nMTUBytes=1450\n",
                "[Network]\nAddress=%(private_ip)s\nNetmask=255.255.0.0" % {
                    "private_ip": env.private_ip
                },
            ))

            run('systemctl restart systemd-networkd')
        elif env.os == "UBUNTU_16_04":
            run("echo \"%s%s%s%s%s\" >> /etc/network/interfaces" %
            (
                "\nauto ens7\n",
                "iface ens7 inet static\n",
                "    netmask 255.255.0.0\n",
                "    mtu 1450\n",
                "    address " + env.private_ip
            ))
            # run('ifup ens7')

    @staticmethod
    def manager():
        cmd = "docker swarm join --token %(token)s %(master)s:2377" % {
            "token": env.token_manager,
            "master": env.master_ip}

        result = run(cmd)
        if bool(re.match(r"(^.*docker swarm leave.*$)", result)):
            run("docker swarm leave --force")
            run(cmd)

    @staticmethod
    def worker():
        cmd = "docker swarm join --token %(token)s %(master)s:2377" % {
            "token": env.token_worker,
            "master": env.master_ip}
        result = run(cmd)
        if bool(re.match(r"(^.*docker swarm leave.*$)", result)):
            run("docker swarm leave --force")
            run(cmd)

    @staticmethod
    def install_docker_ubuntu():
        run("apt-get remove docker docker-engine docker.io")
        run("apt-get update")
        run("apt-get install -y  apt-transport-https ca-certificates \
                curl software-properties-common")
        run("curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -")
        run("add-apt-repository \"deb [arch=amd64] https://download.docker.com/linux/ubuntu \
                $(lsb_release -cs) stable\"")
        run("apt-get update")
        run("apt-get install -y docker-ce")


    @staticmethod
    def config():
        """
        Configure cluster for master, managers and worker nodes
        """
        # Clean from knowed_hosts
        local("ssh-keygen -R %s" % env.master)
        for node in env.managers:
            local("ssh-keygen -R %s" % node["public_ip"])

        for node in env.workers:
            local("ssh-keygen -R %s" % node["public_ip"])

        # Installing docke if is necesary
        with settings(warn_only=True):
            if env.manager_os == "UBUNTU_16_04":
                execute(Cluster.install_docker_ubuntu, hosts=[env.master])
                for manager in env.managers:
                    execute(Cluster.install_docker_ubuntu, hosts=[manager["public_ip"]])
            if env.worker_os == "UBUNTU_16_04":
                for worker in env.workers:
                    execute(Cluster.install_docker_ubuntu, hosts=[worker["public_ip"]])


        with settings(warn_only=True):
            master_ip = env.master_private if env.master_private else env.master
            cmd = "docker swarm init --advertise-addr %s" % master_ip
            result = run(cmd)

            if bool(re.match(r"(^.*docker swarm leave.*$)", result)):
                run("docker swarm leave --force")
                run(cmd)

            token_worker = None
            token_manager = None

            output = run("docker swarm join-token --quiet worker")
            for line in output.splitlines():
                token_worker = line

            output = run("docker swarm join-token --quiet manager")
            for line in output.splitlines():
                token_manager = line

            env.token_manager = token_manager
            env.token_worker = token_worker
            env.master_ip = master_ip
            if env.managers and len(env.managers) > 0:
                for manager in env.managers:
                    execute(Cluster.manager, hosts=[manager["public_ip"]])

            if env.workers and len(env.workers) > 0:
                for worker in env.workers:
                    execute(Cluster.worker, hosts=[worker["public_ip"]])


    @staticmethod
    def registry():
        """
        Install docker registry
        """
        click.echo("\nREGISTRY\n")

    @staticmethod
    def dashboard():
        """
        Install docker portainer and vizualizer
        """
        click.echo("Configuring dashboard...")
        with settings(hide('warnings'), warn_only=True):
            run("mkdir -p /volumes/portainer/data")
            run("docker network create -d overlay portainer")
            run("docker service create \
            --name portainer \
            --publish 9000:9000 \
            --constraint 'node.role == manager' \
            --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
            --mount type=bind,src=/volumes/portainer/data,dst=/data \
            --network portainer \
            portainer/portainer \
            -H unix:///var/run/docker.sock")

            run("docker service create \
            --name=viz \
            --publish=8000:8080/tcp \
            --constraint=node.role==manager \
            --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
            dockersamples/visualizer")

        click.echo("\nDashboard configured!!!...\n")

    @staticmethod
    def proxy():
        """
        Install docker proxy based on http://dockerflow.com
        """
        click.echo("Configuring proxy...")
        with quiet():
            run("mkdir -p %s/proxy" % env.path)

            run("docker network create -d overlay proxy")

            # Volumes should be deleted manually
            run("docker volume create le-certs")
            run("docker volume create dfp-certs")

            proxy_file = resource_filename(Requirement.parse("suarm"), "suarm/tmpl/swarm_proxy.yml")

            with cd('%s/proxy/' % env.path):
                upload_template(
                    filename=proxy_file,
                    destination='%s/proxy/proxy.yml' % env.path,
                    template_dir="./",
                    use_sudo=True,
                )

        with settings(hide('warnings'), warn_only=True):
            # run("docker network ls | grep proxy | awk '{print $1}' | xargs docker network rm")
            # hide('warnings', 'running', 'stdout', 'stderr'),
            run("docker stack deploy --compose-file %s/proxy/proxy.yml proxy" % env.path)

        click.echo("---> Proxy has been installed... :)")

    @staticmethod
    def deploy_app():

        click.echo("---------------------------------")
        click.echo(" Starting Deployment ")
        click.echo("---------------------------------")
        click.echo("MASTER: %s" % env.master)
        click.echo("LABEL: %s" % env.label)
        click.echo("---------------------------------")
        folder = "%s/%s" % (env.path, env.label)
        run("mkdir -p %s" % folder)
        run("mkdir -p %s/data" % folder)
        run("mkdir -p %s/backups" % folder)
        if env.is_ci:
            if env.variables:
                click.echo("Loading [PROJECT_ENVIRONMENT] variables ...")
                f = open('/tmp/.tempenv', 'w')
                f.write(env.variables)
                f.close()
                click.echo("[.environment] created...!!!")
                with cd(folder):
                    upload_template(
                        filename="/tmp/.tempenv",
                        destination='%s/.environment' % folder,
                        template_dir="./",
                    )
                click.echo("[.environment] uploaded and configured...")

        else:
            if isfile(".environment"):
                with cd(folder):
                    upload_template(
                        filename=".environment",
                        destination='%s/.environment' % folder,
                        template_dir="./",
                    )
                    click.echo("---> [.environment] uploaded...!!!")

            if env.registry_host and env.registry_user:
                passwd = getpass("\nPut for password por [%(user)s] in [%(host)s]: " % {
                    "host": env.registry_host,
                    "user": env.registry_user
                })
                if passwd != '':
                    run("docker login %(host)s -u %(user)s -p '%(passwd)s'" % {
                        "host": env.registry_host,
                        "user": env.registry_user,
                        "passwd": passwd
                    })
                else:
                    sys.exit("Password is required...!")

        if isfile("docker-compose.yml"):
            with cd(folder):

                needs_update = isfile(".environment")
                upload_template(
                    filename="./docker-compose.yml",
                    destination='%s/docker-compose.yml' % folder,
                    template_dir="./",
                )
                if needs_update:
                    run("docker stack rm %s" % env.label)
                    from time import sleep
                    sleep(5)
                run("docker stack deploy --compose-file docker-compose.yml %s --with-registry-auth" % env.label)
        else:
            sys.exit("[docker-compose.yml] is required for deployment")


    @staticmethod
    def restart():
        with settings(hide('warnings'), warn_only=True):
            click.echo('\n\n--------------------------------------------------------')
            click.echo("--> HOST: [%s]" % env.host_string)
            run('reboot')
            click.echo('--------------------------------------------------------')


    @staticmethod
    def set_alpha_channel():
        click.echo('\n\n--------------------------------------------------------')
        click.echo("--> HOST: [%s]" % env.host_string)
        run('echo "GROUP=alpha" > /etc/coreos/update.conf')
        run('systemctl restart update-engine')
        run('update_engine_client -update')
        click.echo('--------------------------------------------------------')

    @staticmethod
    def docker_version():
        with settings(hide('warnings'), warn_only=True):
            click.echo('\n\n--------------------------------------------------------')
            click.echo("--> HOST: [%s]" % env.host_string)
            run('docker -v')
            click.echo('--------------------------------------------------------')
