from __future__ import unicode_literals

from fabric.context_managers import lcd, cd
from fabric.contrib.files import exists, upload_template
from fabric.operations import sudo, run
from fabric.state import env


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

    @staticmethod
    def haproxy():
        """
        1. Check if haproxy config exist
        2. Delete current haproxy config
        3. Copy the new haproxy config to server
        4. Restart haproxy
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

        sudo('service haproxy restart')