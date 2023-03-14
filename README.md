<h1 align="center">pycsw CKAN harvester ISO19139</h1>
<p align="center">
<a href="https://github.com/OpenDataGIS/ckan"><img src="https://img.shields.io/badge/%20pycsw-2.6.1-brightgreen" alt="pycsw ersion"></a><a href="https://opensource.org/licenses/MIT"> <img src="https://img.shields.io/badge/license-Unlicense-brightgreen" alt="License: Unlicense"></a> <a href="https://github.com/mjanez/ckan-pycsw/actions/workflows/docker/badge.svg" alt="License: Unlicense"></a>


<p align="center">
    <a href="#overview">Overview</a> •
    <a href="#quick-start">Quick start</a> •
    <a href="#containers">Containers</a>
</p>

**Requirements**:
* [Docker](https://docs.docker.com/get-docker/)

## Overview
Docker compose environment (based on [pycsw](https://github.com/geopython/pycsw)) for development and testing with CKAN Open Data portals.[^1]

Available components:
* **pycsw**: The pycsw app. An [OARec](https://ogcapi.ogc.org/records) and [OGC CSW](https://opengeospatial.org/standards/cat) server implementation written in Python.
* **ckan2pycsw**: Software to achieve interoperability with the open data portals based on CKAN. To do this, ckan2pycsw reads data from an instance using the CKAN API, generates ISO-19115/ISO-19139 [^2] metadata using [pygeometa](https://geopython.github.io/pygeometa/), and populates a [pycsw](https://pycsw.org/) instance that exposes the metadata using CSW and OAI-PMH.

## Quick start
### With docker compose
Configure by changing `PYCSW_URL` and `CKAN_URL` in `docker-compose.yml`, as well as the published port, if needed.

To deploy the environment, `docker compose` will build the images.

```bash
git clone https://github.com/mjanez/ckan-pycsw
cd ckan-pycsw

docker compose up --build
```

>**Note**:<br>
> Deploy the dev `docker-compose_dev.yaml` with:
>
>```bash
> docker compose -f docker-compose_dev.yml up --build
>```


>**Note**:<br>
>If needed, to build a specific container simply run:
>
>```bash
>  docker build -t target_name xxxx/
>```


### Without Docker
Dependencies:
```bash
python3 -m pip install --user pip3
pip3 install pdm
pdm install --no-self
```

Configuration:
```bash
PYCSW_URL=http://localhost:8000 envsubst < pycsw/conf/pycsw.conf.template > pycsw.conf
```

Generate database:
```bash
rm -f cite.db
CKAN_URL=http://ckan:5000 -- pdm run python3 ckan2pycsw/ckan2pycsw.py
```

Run:
```bash
PYCSW_CONFIG=pycsw.conf pdm run python -m pycsw.wsgi
```

## Test
Perform a [GetRecords request](http://localhost:8000/?request=GetRecords&service=CSW&version=3.0.0&typeNames=gmd:MD_Metadata&outputSchema=http://www.isotc211.org/2005/gmd&elementSetName=full).


## Containers
List of *containers*:

* [PyCSW](pycsw/README.md)


### Base images
| Repository | Type | Docker tag | Size | Notes |
| --- | --- | --- | --- | --- |
| python 3.11| base image | `python/python:3.11-slim-bullseye` | 45.57 MB |  - |

### Built images
| Repository | Type | Docker tag | Size | Notes |
| --- | --- | --- | --- | --- |
| mjanez/ckan-pycsw| custom image | `mjanez/ckan-pycsw:latest` | 389MB |  - |

### Network ports settings
| Ports | Container |
| --- | --- |
| 0.0.0.0:8000->8000/tcp | pycsw |

[^1]: Extends the @frafra [coat2pycsw](https://github.com/COATnor/coat2pycsw) package.
[^2]: [INSPIRE dataset and service metadata](https://inspire.ec.europa.eu/id/document/tg/metadata-iso19139) based on ISO/TS 19139:2007. 
