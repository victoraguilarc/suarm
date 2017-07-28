#!/bin/sh
# 1. move to the correct let's encrypt directory for domains
# 2. cat files to make combined .pem's for haproxy
# 3. Restart haproxy
echo "\n-------------------------------------------------------------------------------"
echo " Making certificates for Haproxy :)"
echo "-------------------------------------------------------------------------------"
{% for app in apps %}
cd /etc/letsencrypt/live/{{app['domain']}}
cat fullchain.pem privkey.pem > /etc/haproxy/certs/{{app['domain']}}.pem
echo ">> [{{app['domain']}}] .... OK"
{% endfor %}
echo "-------------------------------------------------------------------------------"

service haproxy reload
