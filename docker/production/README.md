# Production converter patch

Build from the previously deployed immutable image to retain its dependencies,
entrypoint and runtime configuration. Only the three converter source files
are replaced. Do not use development compose configuration in production.

```sh
docker build -f docker/production/Dockerfile --build-arg REVISION="$(git rev-parse HEAD)" -t pabrojast/ckan-pycsw:production-review-20261017 .
```

Regression tests run with the same dependencies, without network access:

```sh
docker run --rm --network none --security-opt label=disable \
  -v "$PWD/tests:/app/tests:ro" --entrypoint /app/.venv/bin/python \
  pabrojast/ckan-pycsw:production-review-20261017 \
  -m unittest discover -s /app/tests -v
```

The converter requires a file-backed SQLite repository. It fetches public CKAN
metadata with bounded, read-only POST requests and stable pagination. POST
bypasses caches that may otherwise return inconsistent GET pages. An incomplete harvest,
conversion error, duplicate or empty result leaves the previous catalogue
untouched. A complete, integrity-checked staging database replaces it atomically;
Gunicorn then reloads gracefully. Optional language defaults to English, as in
the configured catalogue. Source metadata is never modified.
