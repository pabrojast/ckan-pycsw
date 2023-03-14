import os
from configparser import ConfigParser
from urllib.parse import urljoin

import pycsw.core.config
import requests
from pycsw.core import admin, metadata, repository, util
from pygeometa.core import read_mcf
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from shapely.geometry import shape
from model.dataset import Dataset
import debugpy
debugpy.listen(("0.0.0.0", 5678))

URL = os.environ["CKAN_URL"]

def get_datasets(url):
    package_search = urljoin(url, "api/3/action/package_search")
    res = requests.get(package_search, params={"rows": 0})
    end = res.json()["result"]["count"]
    rows = 10
    for start in range(0, end, rows):
        res = requests.get(package_search, params={"start": start, "rows": rows})
        for dataset in res.json()["result"]["results"]:
            if dataset["type"] == "dataset":
                yield dataset

def main():
    pycsw_config = ConfigParser()
    pycsw_config.read_file(open("pycsw.conf"))
    database = pycsw_config.get("repository", "database")
    table_name = pycsw_config.get("repository", "table", fallback="records")
    context = pycsw.core.config.StaticContext()

    pycsw.core.admin.setup_db(
        database,
        table_name,
        "",
    )

    repo = repository.Repository(database, context, table=table_name)

    for dataset in get_datasets(URL):
        dataset_metadata =  Dataset(dataset, URL, "ckan2pycsw/mappings")

        #TODO: Develop the schema selector
        mcf_dict = read_mcf(dataset_metadata.dataset_dict_iso19139_base())
        iso_os = ISO19139OutputSchema()
        xml_string = iso_os.write(mcf_dict)

        record = metadata.parse_record(context, xml_string, repo)[0]
        repo.insert(record, "local", util.get_today_and_now())


if __name__ == "__main__":
    main()