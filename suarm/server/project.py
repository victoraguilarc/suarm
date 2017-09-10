from __future__ import unicode_literals

import os

import sys
from fabric.api import *
from fabric.contrib.files import upload_template, exists

from ..server.config import get_project_src, make_user, make_app


class Project(object):

    @staticmethod
    def config_settings():
        pass

    @staticmethod
    def push():
        """ Push changes to selected server"""
        local("git push %s master" % env.stage)

    @staticmethod
    def install():
        """
        Run intall command.
        """
        python = "DJANGO_SETTINGS_MODULE=config.settings.production ./env/bin/python"
        pip = "./env/bin/pip"

        with cd(get_project_src(env.stage)):
            """
            SETTINGS=config.settings.local
            PYTHON_ENV := =$(SETTINGS) ./env/bin/python
            PIP_ENV := DJANGO_SETTINGS_MODULE=$(SETTINGS) ./env/bin/pip
            virtualenv -p python3 env --always-copy --no-site-packages
            $(PIP_ENV) install -r requirements/production.txt
            mkdir -p var/cache
            mkdir -p var/log
            mkdir -p var/db
            mkdir -p var/run
            mkdir -p var/bin
            $(PYTHON_ENV) manage.py migrate
            $(PYTHON_ENV) manage.py collectstatic \
            -v 0 \
            --noinput \
            --traceback \
            -i django_extensions \
            -i '*.coffee' \
            -i '*.rb' \
            -i '*.scss' \
            -i '*.less' \
            -i '*.sass'
            rm -rf var/cache/*
            rm -rf public/media/cache/*
            """

            if not exists("env"):
                run("virtualenv -p python3 env --always-copy --no-site-packages")

            run("%(pip)s install -r requirements/production.txt" % {"pip": pip})
            run("mkdir -p var/cache var/log var/db var/run var/bin")
            run("%(python)s manage.py migrate" % {"python": python})
            run("%(python)s manage.py collectstatic \
                    -v 0 --noinput --traceback -i django_extensions \
                    -i '*.coffee' -i '*.rb' -i '*.scss' -i '*.less' -i '*.sass'" % {"python": python})

            run("rm -rf var/cache/*")
            run("rm -rf public/media/cache/*")

    @staticmethod
    def clean():
        """
        Clean project logs and cache.
        """
        with cd("%s/var/log" % get_project_src(env.stage)):
            run("rm -rf *")

        with cd("%s/var/cache" % get_project_src(env.stage)):
            run("rm -rf *")

    @staticmethod
    def environment():
        """ Push the environment configuration """

        with cd(get_project_src(env.stage)):
            if os.path.isfile(".environment"):
                upload_template(
                    filename=".environment",
                    destination='.environment',
                    template_dir="./",
                    use_sudo=False,
                )
            else:
                sys.exit("\nYou need [.environment] file to continue with deployment")

    @staticmethod
    def start():
        """
        Start supervisor service.
        """
        sudo("supervisorctl start %s" % env.project)

    @staticmethod
    def restart():
        """
        Restart supervisor service.
        """
        sudo("supervisorctl restart %s" % env.project)

    @staticmethod
    def stop():
        """
        Stop supervisor service.
        """
        sudo("supervisorctl stop %s" % env.project)

    @staticmethod
    def create_superuser():
        """
        Create a superuser to production at selected server.
        """
        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_project_src(env.stage)):
                run("make superuser SETTINGS=config.settings.production")

    @staticmethod
    def reset_env():
        """
        Create a superuser to production at selected server.
        """
        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_project_src(env.stage)):
                run("rm -rf env/")

    @staticmethod
    def run_django_command(command):
        pass

    @staticmethod
    def upload_key():
        """
        Upload  id_rsa.pub file to server.
        This file is obtained from ssh-keygen command.
        """
        try:
            local("ssh-copy-id %(user)s@%(ipv4)s" % {
                "user": make_user(env.project),
                "ipv4": env.ipv4
            })
        except Exception as e:
            raise Exception('Unfulfilled local requirements')




#-------------------------------------------------------------------------------

    def backup():
        """
        Create a database backup
        """

        # Backup DB
        sudo('pg_dump %(app)s > /tmp/%(app)s.sql' % {
            "app": make_app(env.project),
        }, user='postgres')

        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_user_home(env.stage)):
                # Copy backup from temporal
                run("cp /tmp/%(app)s.sql ." %
                    {"app": make_app(env.project)})
                # Compress DB
                run("tar -cvf %(app)s.db.tar %(app)s.sql" %
                    {"app": make_app(env.project)})

                run("rm %(app)s.sql" %
                    {"app": make_app(env.project)})
                # Compress media
                run("tar -cvf %(app)s.media.tar %(app)s/src/public/media/" %
                    {"app": make_app(env.project)})

        # Clean DB from temporal
        sudo('rm /tmp/%(app)s.sql' % {"app": make_app(env.project)})

    @staticmethod
    def download_backup():

        click.echo("Downloading backup patient please ...!!!")

        get(remote_path="%(home)s/%(app)s.db.tar" % {
            "home": get_user_home(env.stage),
            "app": make_app(env.project)
        }, local_path=".", use_sudo=True)
        click.echo("\n---> DB Backup downloaded!")
        get(remote_path="%(home)s/%(app)s.media.tar" % {
            "home": get_user_home(env.stage),
            "app": make_app(env.project)
        }, local_path=".", use_sudo=True)
        click.echo("---> MEDIA Backup downloaded!")
