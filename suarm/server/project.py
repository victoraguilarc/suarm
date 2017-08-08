from __future__ import unicode_literals
from fabric.api import *
from fabric.contrib.files import upload_template

from tools.tasks.config import *


class Project(object):

    @staticmethod
    def push():
        """ Push changes to selected server"""
        local("git push %s master" % env.stage)

    @staticmethod
    def install():
        """
        Run intall command.
        """
        with cd(get_project_src(env.stage)):
            run("make reload SETTINGS=config.settings.production")

    @staticmethod
    def load_corpus():
        """
        Run intall command.
        """
        with cd(get_project_src(env.stage)):
            run("make load_corpus SETTINGS=config.settings.production")

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
            upload_template(
                filename=".environment",
                destination='.environment',
                template_dir="./",
                use_sudo=False,
            )

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
    def corpora():
        """
        Create a superuser to production at selected server.
        """
        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_project_src(env.stage)):
                run("make corpora SETTINGS=config.settings.production")


    @staticmethod
    def reset_env():
        """
        Create a superuser to production at selected server.
        """
        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_project_src(env.stage)):
                run("rm -rf env/")

    @staticmethod
    def backup_logs():
        pass

    @staticmethod
    def backup_db():
        pass

    @staticmethod
    def backup_files():
        pass

    @staticmethod
    def tests():
        pass