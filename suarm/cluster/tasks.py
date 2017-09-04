from __future__ import unicode_literals

import os, sys, re, click
from fabric.context_managers import lcd, cd, quiet, hide
from fabric.contrib.files import exists, upload_template
from fabric.operations import sudo, run, local
from fabric.state import env
from fabric.api import settings
from fabric.tasks import execute

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Cluster(object):

    @staticmethod
    def managers():
        cmd = "docker swarm join --token %(token)s %(master)s:2377" % {
            "token": env.token_manager,
            "master": env.master}

        result = run(cmd)
        if bool(re.match(r"(^.*docker swarm leave.*$)", result)):
            run("docker swarm leave --force")
            run(cmd)

    @staticmethod
    def workers():
        env.hosts = env.workers
        cmd = "docker swarm join --token %(token)s %(master)s:2377" % {
            "token": env.token_worker,
            "master": env.master}
        result = run(cmd)
        if bool(re.match(r"(^.*docker swarm leave.*$)", result)):
            run("docker swarm leave --force")
            run(cmd)

    @staticmethod
    def config():
        """
        Configure cluster for nodes maser and workers
        """

        # for node_ipv4 in env.managers:
        #     local("ssh-keygen -R %s" % node_ipv4)
        #
        # for node_ipv4 in env.workers:
        #     local("ssh-keygen -R %s" % node_ipv4)

        with settings(warn_only=True):
            env.hosts = [env.master]
            cmd = "docker swarm init --advertise-addr %s" % env.master
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

            if env.managers:
                env.hosts = env.managers
                execute(Cluster.managers, hosts=env.managers)

            if env.workers:
                env.hosts = env.workers
                execute(Cluster.workers, hosts=env.workers)

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
            run("mkdir -p /apps/proxy")
            run("docker network create -d overlay proxy")
            with lcd("suarm/tmpl"):
                with cd('/apps/proxy/'):
                    upload_template(
                        filename="swarm_proxy.yml",
                        destination='/apps/proxy/proxy.yml',
                        template_dir="./",
                        use_sudo=True,
                    )

        with settings(hide('warnings'), warn_only=True):
            # run("docker network ls | grep proxy | awk '{print $1}' | xargs docker network rm")
            # hide('warnings', 'running', 'stdout', 'stderr'),
            run("docker stack deploy --compose-file /apps/proxy/proxy.yml proxy")

        click.echo("---> Proxy has been installed... :)")

    @staticmethod
    def deploy_app():
        cluster = env.master
        label = env.label

        if cluster and label:
            click.echo("---------------------------------")
            click.echo("MASTER: %s" % cluster)
            click.echo("LABEL: %s" % label)
            click.echo("---------------------------------")

            folder = "/apps/%s" % label
            run("mkdir -p %s" % folder)
            run("mkdir -p %s/data" % folder)

            if env.develop:
                with cd(folder):
                    upload_template(
                        filename="./.environment",
                        destination='%s/.environment' % folder,
                        template_dir="./",
                    )
                    click.echo("---> [.environment] uploaded...!!!")
            else:
                if env.variables:
                    click.echo("Exist [DEPLOY_ENVIRONMENT] into your env...")
                    f = open('/tmp/.tempenv', 'w')
                    f.write(env.variables)
                    f.close()
                    click.echo("[.environment] created...!!!")
                    with cd(folder):
                        upload_template(
                            filename="/tmp/.tempenv",
                            destination='/apps/%s/.environment' % label,
                            template_dir="./",
                        )
                    click.echo("[.environment] uploaded and configured...")

                else:
                    click.echo("[DEPLOY_ENVIRONMENT] doesn't into your env...")

            if os.path.isfile("docker-compose.yml"):
                with cd("/apps/%s" % label):
                    upload_template(
                        filename="./docker-compose.yml",
                        destination='/apps/%s/docker-compose.yml' % label,
                        template_dir="./",
                    )
                    run("docker stack deploy --compose-file docker-compose.yml %s --with-registry-auth" % env.label)
            else:
                sys.exit("[docker-compose.yml] is required")
        else:
            sys.exit("[DEPLOY_CLUSTER] and [DEPLOY_PROJECT] values are required")
