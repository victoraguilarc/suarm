import sys, os
import click
from fabric.state import env
from fabric.tasks import execute

from suarm.cluster.actions import config_env
from ..cluster.tasks import Cluster


def deploy_app():
    ci = os.environ.get('CONTINUOS_INTEGRATION', False)
    config_env(continuos_integration=ci, cli_deploy=True)
    click.echo("\n---> CI Deployment ...\n" if ci else "\n---> CLI Deployment ...\n")
    execute(Cluster.deploy_app, hosts=[env.master])
