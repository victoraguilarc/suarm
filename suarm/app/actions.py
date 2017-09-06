import sys
import click
from fabric.state import env
from fabric.tasks import execute

from suarm.cluster.actions import config_env
from ..cluster.tasks import Cluster


def deploy_app():
    config_env(deploy=True)
    if not env.is_ci:
        click.echo("\n---> Deployment via CLI directly")
    else:
        click.echo("\n---> Deployment via Continuos Integrations")
    execute(Cluster.deploy_app, hosts=[env.master])
