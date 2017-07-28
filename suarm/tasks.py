from __future__ import unicode_literals

from fabric.context_managers import lcd, cd
from fabric.contrib.files import exists, upload_template
from fabric.operations import sudo, run
from fabric.state import env
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


    @staticmethod
    def restart():
        """
         Restart haproxy
        """
        sudo('service haproxy restart')

    @staticmethod
    def stop():
        """
         Stop haproxy
        """
        sudo('service haproxy stop')

    @staticmethod
    def start():
        """
         Start haproxy
        """
        sudo('service haproxy start')

class Cluster(object):

    @staticmethod
    def config():
        """
        Configure cluster for nodes maser and workers
        """
        print("\nConfiguring cluster...\n")
        if env.type == "master":
            run("docker swarm leave --force")
            run("docker swarm init --advertise-addr %s" % env.ipv4)
            output = run("docker swarm join-token --quiet worker")
            token = None
            for line in output.splitlines():
                token = line
            env.token = token

        elif env.type == "worker":
            run("docker swarm leave --force")
            run("docker swarm join --token %(token)s %(master)s:2377" % {
                "token": env.token,
                "master": env.master
            })
    @staticmethod
    def dashboard():
        """
        Install docker portainer and vizualizer
        """
        print("\nConfiguring dashboard...\n")
        run("mkdir -p /volumes/portainer/data")
        run("docker network create -d overlay portainer")
        run("docker service create \
        --name portainer \
        --publish 80:9000 \
        --constraint 'node.role == manager' \
        --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
        --mount type=bind,src=/volumes/portainer/data,dst=/data \
        --network portainer \
        portainer/portainer \
        -H unix:///var/run/docker.sock")

        run("docker service create \
        --name=viz \
        --publish=8080:8080/tcp \
        --constraint=node.role==manager \
        --mount=type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
        dockersamples/visualizer")
        print("\nDashboard configured!!!...\n")
