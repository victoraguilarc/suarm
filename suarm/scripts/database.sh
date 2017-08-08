#!/bin/bash
# Handle command argument

PROJECT=$(cat servers.json | jq '.develop.project')
PROJECT=$(echo "${PROJECT//\"}")
PASSWORD=$(cat servers.json | jq '.develop.password')
PASSWORD=$(echo "${PASSWORD//\"}")
DATABASE="${PROJECT}_app"
USER="${PROJECT}_user"
TEAM="${PROJECT}_team"

function drop_database()
{
	echo $PROJECT
	echo $DATABASE
	echo $USER
	echo $TEAM
	sudo -H -u postgres bash -c "psql -c \"DROP DATABASE ${DATABASE}\""
#	sudo -H -u postgres bash -c "psql -c \"DROP DATABASE test_${DATABASE}\""
	sudo -H -u postgres bash -c "psql -c \"DROP ROLE IF EXISTS ${USER}\""
}

function create_database()
{
	sudo -H -u postgres bash -c "psql -c \"CREATE USER ${USER} WITH NOCREATEDB NOCREATEUSER ENCRYPTED PASSWORD '${PASSWORD}'\""
	sudo -H -u postgres bash -c "psql -c \"CREATE DATABASE ${DATABASE} WITH OWNER ${USER}\""
#	sudo -H -u postgres bash -c "psql -c \"CREATE DATABASE test_${DATABASE} WITH OWNER ${USER}\""
}

function reset_database()
{
	drop_database
	create_database
}

# Print help / script usage
function usage_message()
{
	cat <<-EOF
		Usage: database.sh <command>
		Available commands are (require superuser permissions):
			create      Create USER and DATABASE for the project.
			reset       Reset USER and DATABASE for the project.
			drop        Drop USER and DATABASE for the project.
	EOF
}

# Handle call with wrong command
function wrong_command()
{
	echo "${0##*/} - unknown command: '${1}'" >&2
	usage_message
}

case "$1" in
	create) create_database;;
	reset) reset_database;;
	drop) drop_database;;
	help|"") usage_message;;
	*) wrong_command "$1";;
esac
