#!/bin/sh
# 0. Renew certificates
# 1. move to the correct let's encrypt directory for domains
# 2. cat files to make combined .pem's for haproxy
# 3. Restart haproxy

echo "\n-------------------------------------------------------------------------------"
echo " Making certificates for WebServer :)"
echo "-------------------------------------------------------------------------------"
cd /etc/letsencrypt/live/%(domain)s
cat /etc/letsencrypt/live/%(domain)s/fullchain.pem /etc/letsencrypt/live/%(domain)s/privkey.pem > /etc/haproxy/certs/%(domain)s.pem
echo ">> [%(domain)s] .... OK"
echo "-------------------------------------------------------------------------------"

service %(service) reload
