FROM python:3.11-slim-bullseye
LABEL maintainer="mnl.janez@gmail.com"

RUN apt-get -q -y update && \
    apt-get install -y wget && \
    DEBIAN_FRONTEND=noninteractive apt-get -yq install gettext-base
ADD https://raw.githubusercontent.com/eficode/wait-for/v2.2.3/wait-for /wait-for
RUN chmod +x /wait-for

RUN python3 -m pip install pdm
WORKDIR /app
COPY pyproject.toml pdm.lock .

RUN pdm install --no-self --group prod

COPY pycsw/conf/pycsw.conf.template pycsw/entrypoint.sh .
COPY ckan2pycsw ckan2pycsw

ENV PYCSW_CONFIG=/app/pycsw.conf
ENV CKAN_URL=http://des.iepnb.es/
ENV TIMEOUT=300

EXPOSE 8000/TCP
ENTRYPOINT ["/bin/bash", "./entrypoint.sh"]
CMD ["pdm", "run", "python3", "-m", "gunicorn", "pycsw.wsgi:application", "-b", "0.0.0.0:8000"]
