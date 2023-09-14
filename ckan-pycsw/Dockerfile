FROM python:3.11.5-slim-bullseye
LABEL maintainer="mnl.janez@gmail.com"

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

RUN apt-get -q -y update && \
    apt-get install -y wget && \
    DEBIAN_FRONTEND=noninteractive apt-get -yq install gettext-base && \
    wget -O /wait-for https://raw.githubusercontent.com/eficode/wait-for/v2.2.3/wait-for && \
    chmod +x /wait-for && \
    python3 -m pip install pdm

WORKDIR ${APP_DIR}
COPY pyproject.toml pdm.lock ./

RUN pdm install --no-self --group prod

COPY ckan-pycsw/conf/pycsw.conf.template ckan-pycsw/docker-entrypoint.d/entrypoint.sh ./
COPY ckan2pycsw ckan2pycsw

EXPOSE ${PYCSW_PORT}/TCP

ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]