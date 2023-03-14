import urllib.parse
import json
import unicodedata
import hashlib
import re
import datetime
import yaml
import os
from urllib.parse import urljoin
from shapely.geometry import shape

class Dataset:
    def __init__(
        self, 
        dataset_raw, 
        base_url: str, 
        mappings_folder: str = "ckan2pycsw/mappings"):
        """
        Constructor of the Dataset class.

        Attributes
        ----------
        dataset_raw: Dataset data from CKAN API.
        base_url: str. URL of the CKAN endpoint retrieved from envvars.
        mappings_folder: str. Folder of the mappings.
        """
        self.dataset_raw = dataset_raw
        self.name = dataset_raw["name"]
        self.url = urljoin(base_url, "dataset/" + self.name + "/")
        self.mappings_folder = mappings_folder

    def get_bbox(self, dataset):
        """
        Get from spatial key in CKAN extras field and convert to JSON Bounding Box.
        
        Return
        ----------
        BBox.
        """
        for extra in dataset["extras"]:
            if extra["key"] == "spatial":
                break
        else:
            return
        return shape(json.loads(extra["value"])).bounds


    def get_map_value(
        self,
        codelist: str,
        category: str):
        """
        Compatibility workaround for codelists.
        
        Parameters
        ----------
        codelist: str. Name of the codelist in the folder.
        category: str. Source value to map.

        Return
        ----------
        Mapping value to codelist category in YAML.
        """
        value = yaml.safe_load(open(os.path.join(self.mappings_folder, codelist + ".yaml"), encoding="utf-8"))

        return value.get(category, category)


    def normalize_datetime(self, timestamp):
        """
        Normalize datetime to ISO 8601 format.
        
        Return
        ----------
        Parsed datetime.
        """
        if not timestamp:
            return timestamp
        parsed = datetime.datetime.fromisoformat(timestamp)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


    # Metadata schemas
    ## TODO: Adapt to CKAN Schema
    # GeoDCAT-AP source scheme
    def dataset_dict_iso19139_geodcatap(self):
        """
        Create a dictionary based on the ISO19139 schema for ingest via pygeometa in pycsw. The customised ckan scheme based on GeoDCAT-AP is used.
        
        Note
        ----------
        CKAN Schema: https://github.com/mjanez/ckanext-scheming/blob/master/ckanext/scheming/ckan_geodcatap.yaml
        ISO19139 Schema: https://github.com/geopython/pygeometa/blob/master/pygeometa/schemas/iso19139/main.j2

        Return
        ----------
        Dataset ISO19139 normalised for use in pygeometa.
        """
        return {
            "mcf": {"version": 1.0},
            "metadata": {
                "identifier": self.dataset_raw["id"],
                "language": "es",
                "charset": "utf8",
                "datestamp": self.normalize_datetime(self.dataset_raw["metadata_modified"]),
                "dataseturi": self.url,
            },
            "spatial": {"datatype": "vector", "geomtype": "polygon"},
            "identification": {
                "language": "en",
                "charset": "utf8",
                "title": {"en": self.dataset_raw["title"]},
                "abstract": {"en": self.dataset_raw["notes"]},
                "edition": self.dataset_raw["version"],
                "dates": {"creation": self.normalize_datetime(self.dataset_raw["metadata_created"])},
                "keywords": {
                    "default": {
                        "keywords": {
                            "en": [tag["name"] for tag in self.dataset_raw["tags"]],
                        }
                    }
                },
                "topiccategory": [
                    self.get_map_value("topic", self.dataset_raw["topic_category"])
                ],
                "extents": {
                    "spatial": [{"bbox": self.get_bbox(self.dataset_raw), "crs": 4326}],
                    "temporal": [
                        {
                            "begin": self.normalize_datetime(self.dataset_raw.get("temporal_start")),
                            "end": self.normalize_datetime(self.dataset_raw.get("temporal_end")),
                        }
                    ],
                },
                "fees": "None",
                "uselimitation": self.dataset_raw["license_id"].replace("_", "-"),
                "accessconstraints": "otherRestrictions",
                "rights": {
                    "en": self.dataset_raw["resource_citations"],
                },
                "url": self.url,
                "status": self.get_map_value("status", self.dataset_raw["status"]),
                "maintenancefrequency": self.dataset_raw["frequency"],
            },
            "contact": {
                "pointOfContact": {
                    "individualname": self.dataset_raw["contact_name"],
                    "email": self.dataset_raw["contact_email"],
                },
                "distributor": {
                    "individualname": self.dataset_raw["publisher_name"],
                    "email": self.dataset_raw["publisher_email"],
                    "url": self.dataset_raw["publisher_uri"],
                },
                "CI_ResponsibleParty": {
                    "individualname": self.dataset_raw["author"],
                    "email": self.dataset_raw["author_email"],
                },
            },
            "distribution": {
                "en": {
                    "url": urljoin(self.url, "zip"),
                    "type": "WWW:LINK",
                    "rel": "canonical",
                    "name": 'ZIP-compressed self.dataset_raw"' + self.dataset_raw["name"] + '"',
                    "description": {
                        "en": 'ZIP-compressed self.dataset_raw"' + self.dataset_raw["name"] + '"',
                    },
                    "function": "download",
                }
            },
        }

    # ckanext-dcat source scheme
    def dataset_dict_iso19139_base(self):
        """
        Create a dictionary based on the ISO19139 schema for ingest via pygeometa in pycsw. The ckanext-dcat schema based on DCAT-AP is used.
        
        Note
        ----------
        CKAN Schema: https://github.com/ckan/ckanext-dcat#rdf-dcat-to-ckan-dataset-mapping
        ISO19139 Schema: https://github.com/geopython/pygeometa/blob/master/pygeometa/schemas/iso19139/main.j2

        Return
        ----------
        Dataset ISO19139 normalised for use in pygeometa.
        """
        return {
            "mcf": {"version": 1.0},
            "metadata": {
                "identifier": self.dataset_raw["id"],
                "language": "es",
                "charset": "utf8",
                "datestamp": self.normalize_datetime(self.dataset_raw["metadata_modified"]),
                "dataseturi": self.url,
            },
            "spatial": {"datatype": "vector", "geomtype": "polygon"},
            "identification": {
                "language": "en",
                "charset": "utf8",
                "title": {"en": self.dataset_raw["title"]},
                "abstract": {"en": self.dataset_raw["notes"]},
                "edition": self.dataset_raw["version"],
                "dates": {"creation": self.normalize_datetime(self.dataset_raw["metadata_created"])},
                "keywords": {
                    "default": {
                        "keywords": {
                            "en": [tag["name"] for tag in self.dataset_raw["tags"]],
                        }
                    }
                },
                "topiccategory": [
                    self.get_map_value("topic", "Biota")
                ],
                "extents": {
                    "spatial": [{"bbox": self.get_bbox(self.dataset_raw), "crs": 4326}],
                    "temporal": [
                        {
                            "begin": self.normalize_datetime(self.dataset_raw.get("temporal_start")),
                            "end": self.normalize_datetime(self.dataset_raw.get("temporal_end")),
                        }
                    ],
                },
                "fees": "None",
                "uselimitation": self.dataset_raw["license_id"].replace("_", "-"),
                "accessconstraints": "otherRestrictions",
                "rights": {
                    "en": self.dataset_raw["access_rights"],
                },
                "url": self.url,
                "status": self.get_map_value("status", self.dataset_raw["status"]),
                "maintenancefrequency": self.dataset_raw["frequency"],
            },
            "contact": {
                "pointOfContact": {
                    "individualname": self.dataset_raw["contact_name"],
                    "email": self.dataset_raw["contact_email"],
                },
                "distributor": {
                    "individualname": self.dataset_raw["publisher_name"],
                    "email": self.dataset_raw["publisher_email"],
                    "url": self.dataset_raw["publisher_uri"],
                },
                "CI_ResponsibleParty": {
                    "individualname": self.dataset_raw["author"],
                    "email": self.dataset_raw["author_email"],
                },
            },
            "distribution": {
                "en": {
                    "url": urljoin(self.url, "zip"),
                    "type": "WWW:LINK",
                    "rel": "canonical",
                    "name": 'ZIP-compressed self.dataset_raw"' + self.dataset_raw["name"] + '"',
                    "description": {
                        "en": 'ZIP-compressed self.dataset_raw"' + self.dataset_raw["name"] + '"',
                    },
                    "function": "download",
                }
            },
        }