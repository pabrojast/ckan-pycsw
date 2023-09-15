FROM python:3.11.5-slim-bullseye
LABEL maintainer="mnl.janez@gmail.com"

# Production non-root user
ENV USERNAME=ckan-pycsw
ENV USER_UID=10001
ENV USER_GID=$USER_UID
# ckan-pycsw envvars
ENV APP_DIR=/app
ENV TZ=UTC
RUN echo ${TZ} > /etc/timezone
ENV PYCSW_CKAN_SCHEMA=iso19139_inspire
ENV PYCSW_CONFIG=${APP_DIR}/pycsw.conf
ENV CKAN_URL=http://localhost:5000/
ENV PYCSW_PORT=8000
ENV PYCSW_URL=http://localhost:${PYCSW_PORT}/
ENV DEV_MODE=False
ENV TIMEOUT=300
ENV PYCSW_CRON_DAYS_INTERVAL=2

WORKDIR ${APP_DIR}

# Create a new non-root user and group, install necessary packages and remove the package list cache
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    chown -R $USERNAME:$USERNAME $APP_DIR && \
    apt-get -q -y update && apt-get install -y --no-install-recommends \
        wget=1.21-1+deb11u1 \
        gettext-base=0.21-4 && \
    wget --progress=dot:mega -O /wait-for https://raw.githubusercontent.com/eficode/wait-for/v2.2.4/wait-for && \
    chmod +x /wait-for && \
    python3 -m pip install --no-cache-dir pdm==2.9.2 && \
    rm -rf /var/lib/apt/lists/*

# Install python dependencies with pdm
COPY pyproject.toml pdm.lock ./
RUN pdm install --no-self --group prod

# Update files
COPY ckan-pycsw/conf/pycsw.conf.template ckan-pycsw/docker-entrypoint.d/entrypoint.sh ./
COPY ckan2pycsw ckan2pycsw

# Switch to non-root user
USER $USERNAME

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]