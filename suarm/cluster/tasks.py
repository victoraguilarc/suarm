from __future__ import unicode_literals

import os, sys, re, click
from getpass import getpass

from fabric.context_managers import cd, quiet, hide
from fabric.contrib.files import upload_template
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
        Configure cluster for master, managers and worker nodes
        """

        for node_ipv4 in env.managers:
            local("ssh-keygen -R %s" % node_ipv4)

        for node_ipv4 in env.workers:
            local("ssh-keygen -R %s" % node_ipv4)

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
            run("mkdir -p %s/proxy" % env.path)
            run("docker network create -d overlay proxy")
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
            if env.has_env:
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

        if os.path.isfile("docker-compose.yml"):
            with cd(folder):
                upload_template(
                    filename="./docker-compose.yml",
                    destination='%s/docker-compose.yml' % folder,
                    template_dir="./",
                )
                run("docker stack deploy --compose-file docker-compose.yml %s --with-registry-auth" % env.label)
        else:
            sys.exit("[docker-compose.yml] is required for deployment")

    @staticmethod
    def config_as_alpha():
        with settings(hide('warnings'), warn_only=True):
            execute(Cluster.set_alpha_channel, hosts=env.managers)
            execute(Cluster.set_alpha_channel, hosts=env.workers)

    @staticmethod
    def restart():
        with settings(hide('warnings'), warn_only=True):
            execute(Cluster.restart_node, hosts=env.managers)
            execute(Cluster.restart_node, hosts=env.workers)

    @staticmethod
    def show_docker_version():
        with settings(hide('warnings'), warn_only=True):
            execute(Cluster.docker_version, hosts=env.managers)
            execute(Cluster.docker_version, hosts=env.workers)

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
        click.echo('\n\n--------------------------------------------------------')
        click.echo("--> HOST: [%s]" % env.host_string)
        run('docker -v')
        click.echo('--------------------------------------------------------')

    @staticmethod
    def restart_node():
        click.echo('\n\n--------------------------------------------------------')
        click.echo("--> HOST: [%s]" % env.host_string)
        run('reboot')
        click.echo('--------------------------------------------------------')
