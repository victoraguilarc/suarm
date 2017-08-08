from __future__ import unicode_literals

import click
from fabric.context_managers import lcd, cd, settings
from fabric.contrib.files import exists, upload_template
from fabric.operations import sudo, run, local
from fabric.state import env

from suarm.server.config import (
    get_value, DB_POSTGRESQL, DB_MYSQL, WS_NGINX,
    WS_APACHE, make_user, get_user_home, HOME_PATH,
    make_team, make_app, get_project_path, get_project_src
)


class Server(object):

    @staticmethod
    def deps():
        """
        Install all server dependencies.
        """
        distro = run("lsb_release -sc", shell=True)
        deps_file = "suarm/scripts/system-%s.txt" % distro
        pkgs = local("grep -vE '^\s*\#' %s  | tr '\n' ' '" % deps_file, capture=True)
        sudo("apt-get install -y %s" % pkgs)

        db_engine = get_value(env.stage, "db_engine", default=DB_POSTGRESQL)
        if db_engine == DB_POSTGRESQL:
            sudo('apt-get install -y postgresql postgresql-contrib libpq-dev')
        elif db_engine == DB_MYSQL:
            sudo('apt-get install -y mysql-server libmysqlclient-dev')

        web_server = get_value(env.stage, "web_server", default=WS_NGINX)
        if web_server == WS_NGINX:
            sudo('apt-get install -y nginx')
        elif web_server == WS_APACHE:
            sudo('apt-get install -y apache2')

        https = get_value(env.stage, "https", default=False)
        if https:
            sudo("apt-get install -y software-properties-common")
            sudo("add-apt-repository -y ppa:certbot/certbot")
            sudo('apt-get update')
            sudo('apt-get install -y certbot')

    @staticmethod
    def haproxy():
        """
        1. Build and Upload haproxy config
        2. Restart haproxy
        """
        click.echo("\nInstalling...\n")
        if not exists('/etc/haproxy'):
            sudo('apt-get update')
            sudo('apt-get upgrade -y')
            sudo('apt-get install -y haproxy')

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
        if get_value(env.stage, "https", default=False):
            sudo("mkdir -p /etc/haproxy/certs")
            for app in env.apps:
                sudo("certbot certonly --standalone -d %(domain)s \
                -m %(email)s -n --agree-tos" % app)
                sudo("bash -c 'cat /etc/letsencrypt/live/%(domain)s/fullchain.pem \
                /etc/letsencrypt/live/%(domain)s/privkey.pem > /etc/haproxy/certs/%(domain)s.pem'" % app)
            sudo("chmod -R go-rwx /etc/haproxy/certs")

            # Copy renew.sh for cronjob
            with lcd("suarm/tmpl"):
                with cd('/usr/local/bin/'):
                    upload_template(
                        filename="le-renew.sh",
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
    def upgrade():
        """
        Update and upgrade server.
        """
        sudo('apt-get update')
        sudo('apt-get upgrade -y')

    @staticmethod
    def pip_cache():
        with settings(user=make_user(env.project), password=env.passwd):
            with cd(get_user_home(env.stage)):
                run("mkdir -p .pip .pip/cache")
                run("printf '[global]\ndownload_cache = %(user_home)s/.pip/cache\n' > %(user_home)s/.pip/pip.conf" % {
                    "user_home": get_user_home(env.stage)
                })

    @staticmethod
    def user():
        """
         Create app user.
        """
        sudo('adduser %(user)s --home %(home_path)s/%(user)s --disabled-password --gecos \"\"' % {
            "user": make_user(env.project),
            "home_path": HOME_PATH,
        })

        sudo('echo \"%(user)s:%(password)s\" | sudo chpasswd' % {
            "user": make_user(env.project),
            "password": env.passwd,
        })

        sudo('mkdir -p %s' % get_user_home(env.stage))

    @staticmethod
    def group():
        """
         Create app group.
        """
        sudo('groupadd --system %s' % make_team(env.project))
        sudo('useradd --system --gid %(team)s --shell /bin/bash --home %(user_home)s %(user)s' %
             {
                 "team": make_team(env.project),
                 "user_home": get_user_home(env.stage),
                 "user": make_user(env.project),
             })

    @staticmethod
    def create_db():
        if env.db_engine == DB_MYSQL:
            Server.mysql()
        elif env.db_engine == DB_POSTGRESQL:
            Server.postgresql()
        else:
            pass

    @staticmethod
    def mysql():
        """
        1. Verify id user exist.
        2. If not user exist create DB user.
        3. Verify if database exist.
        4. If DB not exist create DB and assign to user.
        """

        mysql_user = get_value(env.stage, "mysql_user")
        mysql_pass = get_value(env.stage, "mysql_pass")
        # CREATE DATABASE
        run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'CREATE DATABASE %(database)s;'" % {
            "mysql_user": mysql_user,
            "mysql_password": mysql_pass,
            "database": make_app(env.project),
        })

        # CREATE USER
        run("mysql -u %(mysql_user)s -p%(mysql_password)s -e "
            "'CREATE USER \"%(user)s\"@\"localhost\" IDENTIFIED BY \"%(password)s\";'" % {
                "mysql_user": mysql_user,
                "mysql_password": mysql_pass,
                "user": make_user(env.project),
                "password": env.passwd,
            })

        # GRANT USER TO DB
        run("mysql -u %(mysql_user)s -p%(mysql_password)s -e "
            "'GRANT ALL PRIVILEGES ON %(database)s.* TO \"%(user)s\"@\"localhost\";'" % {
                "mysql_user": mysql_user,
                "mysql_password": mysql_pass,
                "database": make_app(env.project),
                "user": make_user(env.project),
            })

        run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'FLUSH PRIVILEGES;'" % {
            "mysql_user": mysql_user,
            "mysql_password": mysql_pass,
        })

    @staticmethod
    def postgresql():
        """
        1. Create DB user.
        2. Create DB and assign to user.
        """
        sudo('psql -c "CREATE USER %(db_user)s WITH NOCREATEDB NOCREATEUSER ENCRYPTED PASSWORD \'%(db_pass)s\'"' % {
            "db_user": make_user(env.project),
            "db_pass": env.passwd,
        }, user='postgres')

        sudo('psql -c "CREATE DATABASE %(db_name)s WITH OWNER %(db_user)s"' % {
            "db_name": make_app(env.project),
            "db_user": make_user(env.project),
        }, user='postgres')

    @staticmethod
    def git():
        """
        1. Setup bare Git repo.
        2. Create post-receive hook.
        """
        if exists(HOME_PATH) is False:
            sudo('mkdir %s' % HOME_PATH)

        if exists(get_user_home(env.stage)) is False:
            sudo("mkdir %s" % get_user_home(env.stage))

        if exists(get_project_path(env.stage)) is False:
            sudo("mkdir %s" % get_project_path(env.stage))

        if exists(get_project_src(env.stage)) is False:
            sudo("mkdir %s/src" % get_project_path(env.stage))

        with cd(get_project_path(env.stage)):
            sudo('mkdir -p %s.git' % env.project)
            with cd('%s.git' % env.project):
                sudo('git init --bare --shared')
                with lcd("suarm/scripts"):
                    with cd('hooks'):
                        upload_template(
                            filename="post-receive",
                            destination="%(project_path)s/%(project_name)s.git/hooks" % {
                                "project_path": get_project_path(env.stage),
                                "project_name": env.project,
                            },
                            template_dir="./",
                            context={
                                "project_path": get_project_src(env.stage),
                            },
                            use_sudo=True,
                        )
                        sudo('chmod +x post-receive')

            sudo('chown -R %(user)s:%(team)s %(project)s.git' % {
                "user": make_user(env.project),
                "team": make_team(env.project),
                "project": env.project,
            })

    @staticmethod
    def add_remote():
        """
        1. Delete existent server remote git value.
        2. Add existent server remote git value.
        """
        local('git remote remove %s' % env.stage)
        local('git remote add %(remote_name)s %(project_user)s@%(ip_address)s:%(project_path)s/%(project_name)s.git' % {
            "remote_name": env.stage,
            "project_user": make_user(env.project),
            "ip_address": env.ip,
            "project_path": get_project_path(env.stage),
            "project_name": env.project
        })

    @staticmethod
    def nginx():
        """
        1. Remove default nginx config file
        2. Create new config file
        3. Copy local config to remote config
        4. Setup new symbolic link
        """
        # nginx remove default config
        if exists('/etc/nginx/sites-enabled/default'):
            sudo('rm /etc/nginx/sites-enabled/default')

        # nginx config domain file
        if exists('/etc/nginx/sites-enabled/%s' % env.domain):
            sudo('rm /etc/nginx/sites-enabled/%s' % env.domain)
        if exists('/etc/nginx/sites-available/%s' % env.domain):
            sudo('rm /etc/nginx/sites-available/%s' % env.domain)

        # Main domain configuration
        with lcd("suarm/tmpl"):
            with cd('/etc/nginx/sites-available/'):
                upload_template(
                    filename="./nginx.conf",
                    destination='/etc/nginx/sites-available/%s' % env.domain,
                    template_dir="./",
                    context={
                        "project_name": env.project,
                        "project_path": get_project_src(env.stage),
                        "project_url": env.urls,
                        "project_domain": env.domain,
                        "project_https": env.https,
                    },
                    use_jinja=True,
                    use_sudo=True,
                )

        sudo('ln -s /etc/nginx/sites-available/%s /etc/nginx/sites-enabled/' % env.domain)

        # nginx config docs domain file
        if exists('/etc/nginx/sites-enabled/docs.%s' % env.domain):
            sudo('rm /etc/nginx/sites-enabled/docs.%s' % env.domain)
        if exists('/etc/nginx/sites-available/docs.%s' % env.domain):
            sudo('rm /etc/nginx/sites-available/docs.%s' % env.domain)

    @staticmethod
    def gunicorn():
        """
        1. Create new gunicorn start script
        2. Copy local start script template redered to server
        """

        sudo('rm -rf %s/bin' % get_project_src(env.stage))
        sudo('mkdir -p %s/bin' % get_project_src(env.stage))

        with lcd("suarm/scripts"):
            with cd('%s/bin' % get_project_src(env.stage)):
                upload_template(
                    filename='./start.sh',
                    destination='%s/bin/start.sh' % get_project_src(env.stage),
                    template_dir="./",
                    context={
                        "project_name": env.project,
                        "project_path": get_project_src(env.stage),
                        "app_user": make_user(env.project),
                        "app_group": make_team(env.project),
                    },
                    use_jinja=True,
                    use_sudo=True,
                )
                sudo('chmod +x %s/bin/start.sh' % get_project_src(env.stage))

    @staticmethod
    def supervisor():
        """
        1. Create new supervisor config file.
        2. Copy local config to remote config.
        3. Register new command.
        """
        if exists('/etc/supervisor/conf.d/%s.conf' % env.domain):
            sudo('rm /etc/supervisor/conf.d/%s.conf' % env.domain)

        with lcd("suarm/tmpl"):
            with cd('/etc/supervisor/conf.d'):
                upload_template(
                    filename="./supervisor.conf",
                    destination='./%s.conf' % env.domain,
                    template_dir="./",
                    context={
                        "project_name": env.project,
                        "project_path": get_project_src(env.stage),
                        "app_user": make_user(env.project),
                    },
                    use_jinja=True,
                    use_sudo=True,
                )

    @staticmethod
    def restart_services():
        """
        1. Update Supervisor configuration if app supervisor config exist.
        2. Restart nginx.
        3. Restart supervisor.
                """
        if exists('%s/var/log' % get_project_src(env.stage)):
            sudo('supervisorctl reread')
            sudo('supervisorctl update')

        sudo('service nginx restart')
        sudo('service supervisor restart')
        sudo('supervisorctl restart %s' % env.project)

    @staticmethod
    def configure_locales():
        """
        Generate and configure locales in recently installed server.
        """
        sudo("locale-gen en_US.UTF-8")
        sudo("dpkg-reconfigure locales")

    @staticmethod
    def var():
        with cd(get_project_src(env.stage)):
            sudo("mkdir -p var")
            sudo("mkdir -p var/cache var/log var/db var/bin")

    @staticmethod
    def fix_permissions():
        """
         Fix Permissions.
        """
        sudo('chown -R %(user)s:%(group)s %(user_home)s' % {
            "user": make_user(env.project),
            "group": make_team(env.project),
            "user_home": get_user_home(env.stage),
        })

        sudo('chown -R %(user)s:%(group)s %(project_path)s' % {
            "user": make_user(env.project),
            "group": make_team(env.project),
            "project_path": get_project_path(env.stage),
        })

        sudo('chmod -R g+w %s' % get_project_path(env.stage))

        # Permission to WS that require file uploads
        if exists("%s/public/media" % get_project_src(env.stage)):
            sudo('chown -R %(user)s.%(group)s %(media)s' % {
                "user": make_user(env.project),
                "group": "www-data",
                "media": "%s/public/media" % get_project_src(env.stage),
            })

    @staticmethod
    def clean():
        """
        1. kill all user's processes.
        2. Delete app user folder.
        3. Delete project folder.
        4. Delete supervisor and nginx config files.
        5. Drop app and user in database.
        6. Delete app socket.
        7. Delete app group.
        8. Delete app user.
        """
        sudo('pkill -u %s' % make_user(env.project))

        Server.drop_db()

        if exists(get_project_path(env.stage)):
            sudo('rm -rf %s' % get_project_path(env.stage))

        if exists('/etc/supervisor/conf.d/%s.conf' % env.domain):
            sudo('rm -f /etc/supervisor/conf.d/%s.conf' % env.domain)

        if exists('/etc/nginx/sites-enabled/%s' % env.domain):
            sudo('rm -f /etc/nginx/sites-enabled/%s' % env.domain)

        if exists('/etc/nginx/sites-available/%s' % env.domain):
            sudo('rm -f /etc/nginx/sites-available/%s' % env.domain)

        if exists('/etc/nginx/sites-enabled/docs.%s' % env.domain):
            sudo('rm -f /etc/nginx/sites-enabled/docs.%s' % env.domain)

        if exists('/etc/nginx/sites-available/docs.%s' % env.domain):
            sudo('rm -f /etc/nginx/sites-available/docs.%s' % env.domain)

        sudo('rm -rf /tmp/%s.socket' % env.project)
        sudo('groupdel %s' % make_team(env.project))
        sudo('userdel -r %s' % make_user(env.project))
        sudo("rm -rf %s" % get_user_home(env.stage))

    @staticmethod
    def drop_db():
        db_engine = get_value(env.stage, "db_engine", default=DB_POSTGRESQL)

        if db_engine == DB_MYSQL:
            mysql_user = get_value(env.stage, "mysql_user")
            mysql_pass = get_value(env.stage, "mysql_pass")

            run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'DROP DATABASE %(database)s;'" % {
                "mysql_user": mysql_user,
                "mysql_password": mysql_pass,
                "database": make_app(env.project),
            })

            run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'DROP USER \"%(user)s\"@\"localhost\";'" % {
                "mysql_user": mysql_user,
                "mysql_password": mysql_pass,
                "user": make_user(env.project),
            })

            run("mysql -u %(mysql_user)s -p%(mysql_password)s -e 'FLUSH PRIVILEGES;'" % {
                "mysql_user": mysql_user,
                "mysql_password": mysql_pass,
            })

        elif db_engine == DB_POSTGRESQL:
            sudo('psql -c "DROP DATABASE %s"' % make_app(env.project), user='postgres')
            sudo('psql -c "DROP ROLE IF EXISTS %s"' % make_user(env.project), user='postgres')
        else:
            pass

    @staticmethod
    def reset_db():
        Server.drop_db()
        Server.create_db()
