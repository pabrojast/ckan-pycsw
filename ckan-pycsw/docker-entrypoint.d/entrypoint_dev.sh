#!/bin/bash

set -xeuo pipefail

# Change ownership of log and metadata directories
chown -R $USERNAME:$USERNAME ${APP_DIR}/log
chown -R $USERNAME:$USERNAME ${APP_DIR}/metadata

# Switch to the non-root user
su - $USERNAME

envsubst < pycsw.conf.template > pycsw.conf

/wait-for --timeout "$TIMEOUT" "$CKAN_URL" -- pdm run python3 -m ptvsd --host 0.0.0.0 --port "$PYCSW_DEV_PORT" --wait ckan2pycsw/ckan2pycsw.py

exec "$@"
