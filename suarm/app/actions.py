import os

import sys

import click

from fabric.state import env
from fabric.tasks import execute

from suarm.cluster.actions import config_env
from ..cluster.tasks import Cluster


def deploy_app():
    config_env()
    if not env.is_ci:
        click.echo("----------------------------------------")
        click.echo(" Deployment via CLI directly")
        click.echo("----------------------------------------")
        if not env.has_env:
            sys.exit("[.environment] file is required")
    else:
        click.echo("----------------------------------------")
        click.echo(" Deployment via Continuos Integrations")
        click.echo("----------------------------------------")

    execute(Cluster.deploy_app, hosts=[env.master])
