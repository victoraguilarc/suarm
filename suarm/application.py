import os

import sys
from fabric.operations import local
from fabric.state import env
from fabric.tasks import execute
from suarm.tasks import Cluster


def deploy_app():
    mode = os.environ.get('DEPLOY_MODE', False)
    if mode:
        print("------------------------------")
        print(" Production mode")
        print("------------------------------")
        cluster = os.environ.get('DEPLOY_CLUSTER', None)
        label = os.environ.get('DEPLOY_PROJECT', None)
        env.variables = os.environ.get('DEPLOY_ENVIRONMENT', None)
    else:
        print("------------------------------")
        print(" Development mode")
        print("------------------------------")
        if os.path.isfile(".environment"):
            try:
                cluster = local("cat .environment | grep DEPLOY_CLUSTER", capture=True).split("=")[1]
                label = local("cat .environment | grep DEPLOY_PROJECT", capture=True).split("=")[1]
                env.key_filename = local("cat .environment | grep DEPLOY_SSH_KEY", capture=True).split("=")[1]
            except Exception as e:
                sys.exit("[DEPLOY_CLUSTER] and [DEPLOY_PROJECT] and [DEPLOY_SSH_KEY] values are required")
        else:
            sys.exit("[.environment] file is required to make a deploy")

    env.user = 'root'
    env.master = cluster
    env.label = label
    env.develop = not mode
    execute(Cluster.deploy_app, hosts=[env.master])
