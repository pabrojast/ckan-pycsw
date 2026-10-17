# inbuilt libraries
import logging
import pathlib
from configparser import ConfigParser
from urllib.parse import urljoin
import os
from datetime import datetime, time
import subprocess
import signal
import sys
import tempfile
import sqlite3
from sqlalchemy.engine.url import make_url

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
try:
    PYCSW_CRON_HOUR_START = int(os.environ["PYCSW_CRON_HOUR_START"])
except (KeyError, ValueError):
    PYCSW_CRON_HOUR_START = 4
method = "nightly"
URL = os.environ.get("CKAN_URL", 'http://localhost:5000/')
PYCSW_PORT = os.environ.get("PYCSW_PORT", 8000)
PYCSW_URL = os.environ.get("PYCSW_URL", f'http://localhost:{PYCSW_PORT}/')
PYCSW_DEV_PORT = os.environ.get("PYCSW_DEV_PORT", 5678)
APP_DIR = os.environ.get("APP_DIR", "/app")
CKAN_API = "api/3/action/package_search"
PYCSW_CKAN_SCHEMA = os.environ.get("PYCSW_CKAN_SCHEMA", "iso19139_geodcatap")
PYCSW_OUPUT_SCHEMA = os.environ.get("PYCSW_OUPUT_SCHEMA", "iso19139_inspire")
DEV_MODE = os.environ.get("DEV_MODE", False)
PYCSW_CONF = f"{APP_DIR}/pycsw.conf.template" if DEV_MODE == "True" else "pycsw.conf"
MAPPINGS_FOLDER = "ckan2pycsw/mappings"
log_module = "[ckan2pycsw]"
OUPUT_SCHEMA = {
    "iso19139_inspire": ISO19139_inspireOutputSchema,
    "iso19139": ISO19139OutputSchema
}


def get_datasets(base_url):
    """
    Retrieve a generator of CKAN datasets from the specified CKAN instance.

    Parameters
    ----------
    base_url: str. The base URL of the CKAN instance.

    Returns
    -------
    generator: A generator that yields CKAN datasets.

    Raises
    ------
    requests.exceptions.RequestException: If an error occurs while communicating with the CKAN instance.
    """
    package_search = urljoin(base_url.rstrip('/') + '/', CKAN_API)
    seen = set()
    start = 0
    total = None
    while total is None or start < total:
        # A read-only action via POST bypasses independently cached GET pages.
        response = requests.post(package_search, json={
            "start": start, "rows": 100, "sort": "id asc"
        }, timeout=(10, 120))
        response.raise_for_status()
        body = response.json()
        if body.get("success") is not True:
            raise RuntimeError("CKAN package_search failed")
        result = body["result"]
        if total is not None and result["count"] != total:
            raise RuntimeError("CKAN catalogue changed during harvest; retaining previous catalogue")
        total = result["count"]
        datasets = result["results"]
        if not datasets and start < total:
            raise RuntimeError("CKAN returned an incomplete page")
        for dataset in datasets:
            if dataset["id"] in seen:
                raise RuntimeError("CKAN returned a duplicate dataset during pagination")
            seen.add(dataset["id"])
            if dataset.get("private"):
                raise RuntimeError("Refusing to publish a private dataset")
            if dataset.get("type") == "dataset":
                dataset["dcat_type"] = dataset.get("dcat_type") or "http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset"
                yield dataset
        start += len(datasets)
    if len(seen) != total:
        raise RuntimeError("CKAN catalogue count does not match harvested records")


def build_catalogue(database, table_name, datasets):
    """Build a complete SQLite catalogue beside the live file, then replace it atomically."""
    parsed = make_url(database)
    if parsed.drivername != "sqlite" or not parsed.database or parsed.database == ":memory:":
        raise ValueError("Atomic catalogue refresh requires a file-backed SQLite database")
    destination = pathlib.Path(parsed.database).resolve()
    descriptor, staging = tempfile.mkstemp(prefix=destination.name + '.refresh-', suffix='.db', dir=destination.parent)
    os.close(descriptor)
    os.unlink(staging)  # pycsw setup_db creates its own database
    staging_url = 'sqlite:///' + staging
    context = pycsw.core.config.StaticContext()
    repo = None
    count = 0
    try:
        admin.setup_db(staging_url, table_name, "")
        repo = repository.Repository(staging_url, context, table=table_name)
        for dataset in datasets:
            if dataset["dcat_type"].rsplit("/", 1)[-1] not in ("dataset", "series", "service"):
                continue
            converted = Dataset(dataset_raw=dataset, base_url=URL, mappings_folder=MAPPINGS_FOLDER,
                                csw_schema=PYCSW_CKAN_SCHEMA)
            mcf = read_mcf(converted.render_template)
            output = OUPUT_SCHEMA.get(PYCSW_OUPUT_SCHEMA, ISO19139OutputSchema)()
            if PYCSW_OUPUT_SCHEMA in OUPUT_SCHEMA:
                xml = output.write(mcf=mcf, mappings_folder=MAPPINGS_FOLDER)
            else:
                xml = output.write(mcf=mcf)
            record = metadata.parse_record(context, xml, repo)[0]
            repo.insert(record, "local", util.get_today_and_now())
            count += 1
        if not count:
            raise RuntimeError("Refusing to replace the catalogue with zero records")
        repo.session.close()
        repo.engine.dispose()
        repo = None
        with sqlite3.connect(staging) as connection:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Catalogue failed SQLite integrity check")
        os.replace(staging, destination)
        logging.info("Published complete CSW catalogue: %s records", count)
        return count
    finally:
        if repo is not None:
            repo.session.close()
            repo.engine.dispose()
        if os.path.exists(staging):
            os.unlink(staging)


def main():
    """Refresh the catalogue without interrupting requests to the previous version."""
    log_file(APP_DIR + "/log")
    config = ConfigParser()
    with open(PYCSW_CONF) as stream:
        config.read_file(stream)
    database = config.get("repository", "database").replace("${PWD}", os.getcwd())
    table_name = config.get("repository", "table", fallback="records")
    count = build_catalogue(database, table_name, get_datasets(URL))
    # XML files are an export; a failed export must not prevent loading the new database.
    try:
        admin.export_records(pycsw.core.config.StaticContext(), database,
                             table=table_name, xml_dirpath=APP_DIR + "/metadata/")
    except Exception:
        logging.exception("CSW catalogue was published, but its XML export failed")
    return count


def run_scheduler():
    """
    Schedule a recurring task to run at a specific time interval.

    The task will run every `PYCSW_CRON_DAYS_INTERVAL` days, starting at 4:00 a.m.
    The task builds a new catalogue and gracefully reloads Gunicorn after success.

    Returns
    -------
    None
    """
    scheduler = BlockingScheduler(timezone=TZ)
    scheduler_start_date = datetime.now().replace(hour=PYCSW_CRON_HOUR_START, minute=0).strftime('%Y-%m-%d %H:%M:%S')
    scheduler.add_job(run_tasks, "interval", days=PYCSW_CRON_DAYS_INTERVAL, start_date=scheduler_start_date)
    scheduler.start()

def run_tasks():
    """Keep serving the previous catalogue until its replacement is complete."""
    main()  # Any harvest/conversion error leaves both the live database and server intact.
    pidfile = pathlib.Path(APP_DIR) / "gunicorn.pid"
    if pidfile.exists():
        try:
            process = psutil.Process(int(pidfile.read_text().strip()))
            if "gunicorn" not in ' '.join(process.cmdline()):
                raise RuntimeError("Gunicorn PID file points to another process")
            process.send_signal(signal.SIGHUP)
            return
        except psutil.NoSuchProcess:
            pidfile.unlink(missing_ok=True)
    subprocess.Popen([sys.executable, "-m", "gunicorn", "pycsw.wsgi:application",
                      "-b", f"0.0.0.0:{PYCSW_PORT}", "--pid", str(pidfile)])

if __name__ == "__main__":
    if str(DEV_MODE).lower() == "true":
        # Allow other computers to attach to ptvsd at this IP address and port.
        ptvsd.enable_attach(address=("0.0.0.0", PYCSW_DEV_PORT), redirect_output=True)

        # Pause the program until a remote debugger is attached
        ptvsd.wait_for_attach()
        main()
    # Launch a cronjob 
    else:
        run_tasks()
        run_scheduler()