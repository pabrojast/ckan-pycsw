# inbuilt libraries
import logging
import pathlib
from configparser import ConfigParser
from urllib.parse import urljoin
import os
from datetime import datetime, timedelta
import subprocess
import time

# third-party libraries
import psutil
import requests
import pycsw.core.config
from pycsw.core import admin, metadata, repository, util
from pygeometa.core import read_mcf
from pygeometa.schemas.iso19139 import ISO19139OutputSchema
from apscheduler.schedulers.blocking import BlockingScheduler

# custom functions
from config.log import log_file

# custom classes
from model.dataset import Dataset
from schemas.pygeometa.iso19139_inspire import ISO19139_inspireOutputSchema

# debug
import ptvsd

# Ennvars
TZ = os.environ.get("TZ", "TZ")
try:
    PYCSW_CRON_DAYS_INTERVAL = int(os.environ["PYCSW_CRON_DAYS_INTERVAL"])
except (KeyError, ValueError):
    PYCSW_CRON_DAYS_INTERVAL = 3
method = "nightly"
URL = os.environ["CKAN_URL"]
PYCSW_URL = os.environ["PYCSW_URL"]
PYCSW_PORT = os.environ["PYCSW_PORT"]
APP_DIR = os.environ.get("APP_DIR", "/app")
CKAN_API = "api/3/action/package_search"
PYCSW_CKAN_SCHEMA = os.environ.get("PYCSW_CKAN_SCHEMA", "iso19139_geodcatap")
PYCSW_OUPUT_SCHEMA = os.environ.get("PYCSW_OUPUT_SCHEMA", "iso19139_inspire")
DEV_MODE = os.environ.get("DEV_MODE", None)
PYCSW_CONF = f"{APP_DIR}/pycsw.conf.template" if DEV_MODE == "True" else "pycsw.conf"
MAPPINGS_FOLDER = "ckan2pycsw/mappings"
log_module = "[ckan2pycsw]"
OUPUT_SCHEMA = {
    "iso19139_inspire": ISO19139_inspireOutputSchema,
    "iso19139": ISO19139OutputSchema
}


def get_datasets(base_url):
    try:
        if not base_url.endswith("/"):
                base_url += "/"
        package_search = urljoin(base_url, CKAN_API)
        res = requests.get(package_search, params={"rows": 0})
        end = res.json()["result"]["count"]
        rows = 10
        for start in range(0, end, rows):
            res = requests.get(package_search, params={"start": start, "rows": rows})
            for dataset in res.json()["result"]["results"]:
                if dataset["type"] == "dataset":
                    yield dataset
    except Exception as e:
        logging.error(f"{log_module}:ckan2pycsw | No metadata in CKAN: {base_url} | Error: {e}")

def main():
    log_file(APP_DIR + "/log")
    logging.info(f"{log_module}:ckan2pycsw | Version: 0.1")
    pycsw_config = ConfigParser()
    pycsw_config.read_file(open(PYCSW_CONF))
    database_raw = pycsw_config.get("repository", "database")
    database = database_raw.replace("${PWD}", os.getcwd()) if DEV_MODE == "True" else database_raw
    table_name = pycsw_config.get("repository", "table", fallback="records")
    context = pycsw.core.config.StaticContext()

    # check if cite.db exists in folder, and delete it if it does
    database_path =  "/" + database.split("//")[-1]
    
    if pathlib.Path(database_path).exists():
        os.remove(database_path)
    pycsw.core.admin.setup_db(
        database,
        table_name,
        "",
    )

    repo = repository.Repository(database, context, table=table_name)

    dcat_type = [
         "dataset", 
         "series", 
         "service"
         ]
    
    # Only iterate over dataset if dataset["dcat_type"] in dcat_type
    for dataset in (d for d in get_datasets(URL) if d["dcat_type"].rsplit("/", 1)[-1] in dcat_type):
                # Add a counter of errors and valids datasets

                d_dcat_type = dataset["dcat_type"].rsplit("/", 1)[-1]
                logging.info(f"{log_module}:ckan2pycsw | Metadata: {dataset['name']} [DCAT Type: {d_dcat_type.capitalize()}]")
                try:
                    dataset_metadata =  Dataset(dataset_raw=dataset, base_url=URL, mappings_folder=MAPPINGS_FOLDER,  csw_schema=PYCSW_CKAN_SCHEMA)
                    mcf_dict = read_mcf(dataset_metadata.render_template)
                    
                    # Select an output schema based on OUPUT_SCHEMA if not exists use ISO19139
                    if PYCSW_OUPUT_SCHEMA in OUPUT_SCHEMA:
                        iso_os = OUPUT_SCHEMA[PYCSW_OUPUT_SCHEMA]()
                        xml_string = iso_os.write(mcf=mcf_dict, mappings_folder=MAPPINGS_FOLDER)
                    else:
                        iso_os = ISO19139OutputSchema()
                        xml_string = iso_os.write(mcf=mcf_dict)


                    #TODO: DELETE Dumps to log
                    #print(xml_string,  file=open(APP_DIR + "/log/demo.xml", "w", encoding="utf-8"))

                    # parse xml
                    record = metadata.parse_record(context, xml_string, repo)[0]
                    repo.insert(record, "local", util.get_today_and_now())
                except Exception as e:
                    logging.error(f"{log_module}:ckan2pycsw | Fail when transform record from CKAN for: {dataset['name']} [DCAT Type: {d_dcat_type.capitalize()}] Error: {e}")
                    continue

    logging.info(f"{log_module}:ckan2pycsw | Create a CSW Endpoint at: {PYCSW_URL}")

    # Export records to Folder
    pycsw.core.admin.export_records(
         context, 
         database, 
         table=table_name, 
         xml_dirpath=APP_DIR + "/metadata/")


def run_scheduler():
    scheduler = BlockingScheduler(timezone=TZ)
    scheduler.add_job(run_tasks, "interval", days=PYCSW_CRON_DAYS_INTERVAL, next_run_time=datetime.now())
    scheduler.start()

def run_tasks():
    """
    Check if gunicorn is running. Kill any gunicorn process with "gunicorn" or "pycsw.wsgi:application" in its name or command line.
    Execute the main function. Restart gunicorn after the main function finishes.
    """
    log_file(APP_DIR + "/log")
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        if "gunicorn" in proc.info["name"] or "pycsw.wsgi:application" in ' '.join(proc.info["cmdline"]):
            print(f"Stopping gunicorn process with PID {proc.info['pid']}...")
            proc.kill()
            time.sleep(5)  # Wait for the gunicorn process to fully stop

    # Execute the main function
    main()

    # Restart gunicorn after the main function finishes
    try:
        subprocess.Popen(["pdm", "run", "python3", "-m", "gunicorn", "pycsw.wsgi:application", "-b", f"0.0.0.0:{PYCSW_PORT}"])
    except Exception as e:
        logging.error(f"{log_module}:ckan2pycsw | Error starting gunicorn: {e}")

if __name__ == "__main__":
    if DEV_MODE == True or DEV_MODE == "True":
        # Allow other computers to attach to ptvsd at this IP address and port.
        ptvsd.enable_attach(address=("0.0.0.0", 5678), redirect_output=True)

        # Pause the program until a remote debugger is attached
        ptvsd.wait_for_attach()
        main()
    else:
        run_scheduler()
    