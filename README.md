<h1 align="center">pycsw CKAN harvester ISO19139</h1>
<p align="center">
<a href="https://github.dev/mjanez/ckan-pycsw"><img src="https://img.shields.io/badge/%20pycsw-2.6.1-brightgreen" alt="pycsw ersion"></a><a href="https://opensource.org/licenses/MIT"> <img src="https://img.shields.io/badge/license-Unlicense-brightgreen" alt="License: Unlicense"></a> <a href="https://github.com/mjanez/ckan-pycsw/actions/workflows/docker/badge.svg" alt="License: Unlicense"></a>


<p align="center">
    <a href="#overview">Overview</a> •
    <a href="#quick-start">Quick start</a> •
    <a href="#schema-development">Schema development</a> •
    <a href="#test">Test</a> •
    <a href="#debug">Debug</a> •
    <a href="#containers">Containers</a>
</p>

**Requirements**:
* [Docker](https://docs.docker.com/get-docker/)

## Overview
Docker compose environment (based on [pycsw](https://github.com/geopython/pycsw)) for development and testing with CKAN Open Data portals.[^1]

>**Note**<br>
> It can be easily tested with a CKAN-type Open Data portal deployment: [mjanez/ckan-docker](https://github.com/mjanez/ckan-docker)[^2].

Available components:
* **pycsw**: The pycsw app. An [OARec](https://ogcapi.ogc.org/records) and [OGC CSW](https://opengeospatial.org/standards/cat) server implementation written in Python.
* **ckan2pycsw**: Software to achieve interoperability with the open data portals based on CKAN. To do this, `ckan2pycsw` reads data from an instance using the CKAN API, generates INSPIRE ISO-19115/ISO-19139 [^3] metadata using [pygeometa](https://geopython.github.io/pygeometa/), or another custom schema, and populates a [pycsw](https://pycsw.org/) instance that exposes the metadata using CSW and OAI-PMH.

## Quick start
### With docker compose
Copy the `.env.example` template and configure by changing the `.env` file. Change `PYCSW_URL` and `CKAN_URL`,  as well as the published port `PYCSW_PORT`, if needed.

    ```shell
    cp .env.example .env
    ```

Select the CKAN Schema (`PYCSW_CKAN_SCHEMA`), and the pycsw output schema (`PYCSW_OUPUT_SCHEMA`).
- Default: 
    ```ini
    PYCSW_CKAN_SCHEMA=iso19139_geodcatap
    PYCSW_OUPUT_SCHEMA=iso19139_inspire
    ```
- Avalaible:
  * CKAN metadata schema (`PYCSW_CKAN_SCHEMA`):
    * `iso19139_geodcatap`, **default**: [WIP] Schema based on [GeoDCAT-AP custom dataset schema](https://github.com/mjanez/ckanext-scheming).
    * `iso19139_base`: [WIP] Base schema.

  * pycsw metadata schema (`PYCSW_OUPUT_SCHEMA`):
    * `iso19139_inspire`, **default**: Customised schema based on ISO 19139 INSPIRE metadata schema.
    * `iso19139`: Standard pycsw schema based on ISO 19139.

>**Note**<br>
> The output pycsw schema (`iso19139_inspire`), to comply with INSPIRE ISO 19139 is WIP. The validation of the dataset/series is complete and conforms to the [INSPIRE reference validator](https://inspire.ec.europa.eu/validator/home/index.html) datasets and dataset series (Conformance Class 1, 2, 2b and 2c). In contrast, spatial data services still fail in only 1 dimension [WIP]. 

To deploy the environment, `docker compose` will build the latest source in the repo.

If you can deploy a `5 minutes` image, use the stable image ([`ghcr.io/mjanez/ckan-pycsw:main`](https://github.com/mjanez/ckan-pycsw/pkgs/container/ckan-pycsw)) with [`docker-compose.ghcr.yml`](/docker-compose.ghcr.yml)

```bash
git clone https://github.com/mjanez/ckan-pycsw
cd ckan-pycsw

docker compose up --build

# Github main registry image
docker compose -f docker-compose.ghcr.yml --build

# Or detached mode
docker compose up -d --build
```

>**Note**:<br>
> Deploy the dev (multistage build) `docker-compose.dev.yml` with:
>
>```bash
> docker compose -f docker-compose.dev.yml up --build
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
PYCSW_URL=http://localhost:8000 envsubst < ckan-pycsw/conf/pycsw.conf.template > pycsw.conf
```

Generate database:
```bash
rm -f cite.db
CKAN_URL=http://localhost:5000 pdm run python3 ckan2pycsw/ckan2pycsw.py
```

Run:
```bash
PYCSW_CONFIG=pycsw.conf pdm run python -m pycsw.wsgi
```

## Schema development
User-defined metadata schemas can be added, both for CKAN metadata input: `ckan2pycsw/schemas/ckan/*` and for output schemas in pycsw: `ckan2pycsw/schemas/pygeometa/*`.

### New input Metadata schema (CKAN)
You can customise and extend the metadata schemas that serve as templates to import as many metadata elements as possible from a custom schema into CKAN. e.g. Based on a custom schema from [`ckanext-scheming`](https://github.com/ckan/ckanext-scheming).

#### Sample workflow
1. Create a new folder in [`schemas/ckan/`](./ckan2pycsw/schemas/pygeometa/) with the name intended for the schema. e.g. `iso19139_spain`.

2. Create the `main.j2` with the Jinja template to render the metadata.Examples in: [`schemas/ckan/iso19139_geodcatap](/ckan2pycsw/schemas/ckan/iso19139_geodcatap/)

3. Add all needed mappings (`.yaml`) to a new folder in [`ckan2pycsw/mappings/`](./ckan2pycsw/mappings/). e.g. `iso19139_spain`

4. Update [`ckan2pycsw/mappings/ckan-pycsw_assigments.yaml`](/ckan2pycsw/mappings/ckan-pycsw_assigments.yaml) to include the pycsw and ckan schema mapping. e.g.
    ```yaml
    iso19139_geodcatap: ckan_geodcatap
    iso19139_base: ckan_base
    iso19139_inspire: inspire
    ...
    iso19139_spain: iso19139_spain
    ```

5. Modify `.env` to select the new `PYCSW_CKAN_SCHEMA`:

    ```ini
    PYCSW_CKAN_SCHEMA=iso19139_spain
    PYCSW_OUPUT_SCHEMA=iso19139
    ```


### New ouput CSW Metadata schema (pycsw/pygeometa)
New metadata schemas can be extended or added to convert elements extracted from CKAN into standard metadata profiles that can be exposed in the pycsw CSW Catalogue.

#### Sample workflow
1. Create a new folder in [`schemas/pygeometa/`](./ckan2pycsw/schemas/pygeometa/) with the name intended for the schema. e.g. `iso19139_spain`.

2. Add a `__init__.py` file with the extended pygeometa schema class. e.g. 
    ```python
    import ast
    import logging
    import os
    from typing import Union

    from lxml import etree
    from owslib.iso import CI_OnlineResource, CI_ResponsibleParty, MD_Metadata

    from pygeometa.schemas.base import BaseOutputSchema
    from model.template import render_j2_template

    LOGGER = logging.getLogger(__name__)
    THISDIR = os.path.dirname(os.path.realpath(__file__))


    class ISO19139_spainOutputSchema(BaseOutputSchema):
        """ISO 19139 - Spain output schema"""

        def __init__(self):
            """
            Initialize object

            :returns: pygeometa.schemas.base.BaseOutputSchema
            """

            super().__init__('iso19139_spain', 'xml', THISDIR)
    ...
    ```

3. Create the `main.j2` with the Jinja template to render the metadata, macros can be added for more specific templates, for example: `iso19139_inspire-regulation.j2`, or `contact.j2`, more examples in: [`schemas/pygeometa/iso19139_inspire`](./ckan2pycsw/schemas/iso19139_inspire)

4. Add the Python class and the schema identifier to [`ckan2pycsw.py`](./ckan2pycsw/ckan2pycsw.py), e.g.
    ```python

    from schemas.pygeometa.iso19139_inspire import ISO19139_inspireOutputSchema, ISO19139_spainOutputSchema

    ...

    OUPUT_SCHEMA = {
        'iso19139_inspire': ISO19139_inspireOutputSchema,
        'iso19139': ISO19139OutputSchema,
        'iso19139_spain: ISO19139_spainOutputSchema
    }
    ```

5. Add all mappings (`.yaml`) to a new folder in [`ckan2pycsw/mappings/`](./ckan2pycsw/mappings/). e.g. `iso19139_spain`

6. Update [`ckan2pycsw/mappings/ckan-pycsw_assigments.yaml`](/ckan2pycsw/mappings/ckan-pycsw_assigments.yaml) to include the pycsw and ckan schema mapping. e.g.
    ```yaml
    iso19139_geodcatap: ckan_geodcatap
    iso19139_base: ckan_base
    iso19139_inspire: inspire
    ...
    iso19139_spain: iso19139_spain
    ```

7. Modify `.env` to select the new `PYCSW_OUPUT_SCHEMA`:

    ```ini
    PYCSW_CKAN_SCHEMA=iso19139_geodcatap
    PYCSW_OUPUT_SCHEMA=iso19139_spain
    ```

## Test
Perform a `GetRecords` request and return all:

    {PYCSW_URL}?request=GetRecords&service=CSW&version=3.0.0&typeNames=gmd:MD_Metadata&outputSchema=http://www.isotc211.org/2005/gmd&elementSetName=full


- The `ckan-pycsw` logs will be created in the [`/log`](/log/) folder.
- Metadata records in `XML` format ([ISO 19139](https://www.iso.org/standard/67253.html)) are stored in the [`/metadata`](/metadata/) folder.

>**Note**
> The `GetRecords` operation allows clients to discover resources (datasets). The response is an `XML` document and the output schema can be specified.

## Debug
### VSCode
#### Python debugger with Docker
1. Build and run container.
2. Attach Visual Studio Code to container.
3. Start debugging on `ckan2pycsw.py` Python file (`Debug the currently active Python file`) in the container.

#### Python debugger without Docker
1. Update the previously created `.env` file in the root of the `ckan-ogc` repo and move it to: [`/ckan2pycsw`](/ckan2pycsw)
2. Open [`ckan2pycsw.py`](/ckan2pycsw/ckan2pycsw.py).
3. Start debugging on `ckan2pycsw.py` Python file (`Debug the currently active Python file`). 

>**Note**<br>
> By default, the Python extension looks for and loads a file named `.env` in the current workspace folder. More info about Python debugger and [Enviromental variables use](https://code.visualstudio.com/docs/python/environments#_environment-variables).

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
| mjanez/ckan-pycsw| custom image | `mjanez/ckan-pycsw:latest` | 175 MB |  Dev & Test latest version. |
| mjanez/ckan-pycsw| custom image | `mjanez/ckan-pycsw:main` | 175 MB |  Stable version. |

>**Note**<br>
> GHCR and Dev `Dockerfiles` using `main` images as base.

### Network ports settings
| Ports | Container |
| --- | --- |
| 0.0.0.0:8000->8000/tcp | pycsw |
| 0.0.0.0:5678->5678/tcp | ckan-pycsw debug (debugpy) |


[^1]: Extends the @frafra [coat2pycsw](https://github.com/COATnor/coat2pycsw) package.
[^2]: A custom installation of Docker Compose with specific extensions for spatial data and [GeoDCAT-AP](https://github.com/SEMICeu/GeoDCAT-AP)/[INSPIRE](https://github.com/INSPIRE-MIF/technical-guidelines) metadata [profiles](https://en.wikipedia.org/wiki/Geospatial_metadata).
[^3]: [INSPIRE dataset and service metadata](https://inspire.ec.europa.eu/id/document/tg/metadata-iso19139) based on ISO/TS 19139:2007. 
