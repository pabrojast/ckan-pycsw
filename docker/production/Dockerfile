FROM pabrojast/ckan-pycsw@sha256:4cbb7c68aa69a60b21168a02a74293ecbc198865d35c8c41afdcc9e00504f51a
ARG REVISION
LABEL org.opencontainers.image.source="https://github.com/pabrojast/ckan-pycsw" \
      org.opencontainers.image.revision=$REVISION
COPY ckan2pycsw/ckan2pycsw.py /app/ckan2pycsw/ckan2pycsw.py
COPY ckan2pycsw/model/template.py /app/ckan2pycsw/model/template.py
COPY ckan2pycsw/schemas/ckan/iso19139_geodcatap/main.j2 /app/ckan2pycsw/schemas/ckan/iso19139_geodcatap/main.j2
