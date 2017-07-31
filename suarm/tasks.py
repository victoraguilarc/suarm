from __future__ import unicode_literals

import re
from fabric.context_managers import lcd, cd, quiet, hide
from fabric.contrib.files import exists, upload_template
from fabric.operations import sudo, run
from fabric.state import env
from fabric.api import settings
from fabric.tasks import execute

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class Server(object):

    @staticmethod
    def install():
        """
        Install all server dependencies.
        """
        print("\nPreparing...\n")
        if not exists('/etc/haproxy'):
            sudo('apt-get update')
            sudo('apt-get upgrade -y')
            sudo('apt-get install -y haproxy')
            sudo('apt-get install -y software-properties-common')
            sudo('add-apt-repository ppa:certbot/certbot')
            sudo('apt-get update')
            sudo('apt-get install -y certbot')


    @staticmethod
    def haproxy():
        """
        1. Build and Upload haproxy config
        2. Restart haproxy
        """
        # nginx remove default config
        if exists('/etc/haproxy/haproxy.cfg'):
            sudo('rm /etc/haproxy/haproxy.cfg')

        # Main domain configuration
        with lcd("tmpl"):
            with cd('/etc/haproxy/'):
                upload_template(
                    filename="haproxy.cfg",
                    destination='/etc/haproxy/haproxy.cfg',
                    template_dir="./",
                    context={
                        "admin": {"username": "admin", "password": "1029384756"},
                        "apps": env.apps,
                        "cluster": env.cluster
                    },
                    use_jinja=True,
                    use_sudo=True,
                )

    @staticmethod
    def letsencrypt():
        """
        1. Obtain certificates for apps
        2. Setting Up autorenew logic
        """
        sudo("mkdir -p /etc/haproxy/certs")
        for app in env.apps:
            sudo("certbot certonly --standalone -d %(domain)s \
            -m %(email)s -n --agree-tos" % app)
            sudo("bash -c 'cat /etc/letsencrypt/live/%(domain)s/fullchain.pem \
            /etc/letsencrypt/live/%(domain)s/privkey.pem > /etc/haproxy/certs/%(domain)s.pem'" % app)
        sudo("chmod -R go-rwx /etc/haproxy/certs")

        # Copy renew.sh for cronjob
        with lcd("tmpl"):
            with cd('/usr/local/bin/'):
                upload_template(
                    filename="renew.sh",
                    destination='/usr/local/bin/renew.sh',
                    template_dir="./",
                    context={
                        "apps": env.apps,
                        "cluster": env.cluster
                    },
                    use_jinja=True,
                    use_sudo=True,
                )
        sudo("chmod u+x /usr/local/bin/renew.sh")
        sudo("/usr/local/bin/renew.sh")
        sudo("certbot renew")
        repetition = '30 2 * * *'
        cmd = '/usr/bin/certbot renew --renew-hook \"/usr/local/bin/renew.sh\" >> /var/log/le-renewal.log'
        run('crontab -l | grep -v "%s"  | crontab -' % cmd)
        run('crontab -l | { cat; echo "%s %s"; } | crontab -' % (repetition, cmd))

    @staticmethod
    def reboot():
        """
         Restart haproxy
        """
        sudo('reboot')


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
        print("\nREGISTRY\n")


    @staticmethod
    def dashboard():
        """
        Install docker portainer and vizualizer
        """
        print("Configuring dashboard...")
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

        print("\nDashboard configured!!!...\n")


    @staticmethod
    def proxy():
        """
        Install docker proxy based on http://dockerflow.com
        """
        print("Configuring proxy...")
        with quiet():
            run("mkdir -p /apps/proxy")
            run("docker network create -d overlay proxy")
            with lcd("tmpl"):
                with cd('/apps/proxy/'):
                    upload_template(
                        filename="proxy.yml",
                        destination='/apps/proxy/proxy.yml',
                        template_dir="./",
                        use_sudo=True,
                    )

        with settings(hide('warnings'), warn_only=True):
            # run("docker network ls | grep proxy | awk '{print $1}' | xargs docker network rm")
            # hide('warnings', 'running', 'stdout', 'stderr'),
            run("docker stack deploy --compose-file /apps/proxy/proxy.yml proxy")

        print("---> Proxy has been installed... :)")

    @staticmethod
    def deploy_app():
        cluster = env.master
        label = env.label

        if cluster and label:
            print("CLUSTER: %s" % cluster)
            print("LABEL: %s" % label)

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
                    print("---> [.environment] uploaded...!!!")
            else:
                # Create .environment from env variables
                pass

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
