import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'ckan2pycsw'))
from model.dataset import Dataset
from pygeometa.core import read_mcf
from schemas.pygeometa.iso19139_inspire import ISO19139_inspireOutputSchema
from lxml import etree


class MetadataConversionTests(unittest.TestCase):
    def record(self):
        return dict(id='qa-id', name='qa-record', type='dataset',
                    dcat_type='http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
                    title='River survey', notes='Water observations',
                    metadata_created='2026-01-01T00:00:00',
                    metadata_modified='2026-01-02T00:00:00', resources=[])

    def convert(self, record):
        return Dataset(copy.deepcopy(record), base_url='https://catalog.example/',
                       csw_schema='iso19139_geodcatap').render_template

    def test_missing_optional_metadata(self):
        result = self.convert(self.record())
        self.assertEqual(result['metadata']['identifier'], 'qa-id')
        self.assertEqual(result['identification']['title'], 'River survey')
        self.assertEqual(result['identification']['extents']['spatial'], [])

    def test_serialized_geometry_is_preserved_without_mutating_input(self):
        record = self.record()
        record['spatial'] = json.dumps({'type': 'Point', 'coordinates': [-70, -33]})
        before = copy.deepcopy(record)
        result = Dataset(record, base_url='https://catalog.example/',
                         csw_schema='iso19139_geodcatap').render_template
        self.assertEqual(json.loads(result['identification']['extents']['spatial'][0]['bbox']),
                         [-70, -33, -70, -33])
        self.assertEqual(record, before)

    def test_quotes_unicode_and_backslashes_round_trip(self):
        record = self.record()
        record['language'] = 'http://publications.europa.eu/resource/authority/language/ENG'
        record['title'] = 'River "A" — measurement'
        record['notes'] = 'Line one\nLine two: C:\\surveys\\water, }'
        result = self.convert(record)
        self.assertEqual(result['identification']['title'], record['title'])
        self.assertEqual(result['identification']['abstract'], record['notes'])

    def test_partial_contacts_and_multiple_same_format_resources(self):
        record = self.record()
        record.update(language='http://publications.europa.eu/resource/authority/language/ENG',
                      publisher_name='Research Institute', author_name='Researcher')
        record['resources'] = [
            dict(id='one', name='First "station"', format='CSV', url='https://example.test/one'),
            dict(id='two', name='Second station', format='CSV', url='https://example.test/two'),
            dict(id='three', name='Unspecified format', format='', url='https://example.test/three'),
        ]
        result = self.convert(record)
        urls = {item['url'] for item in result['distribution'].values()}
        self.assertEqual(urls, {r['url'] for r in record['resources']})
        xml = ISO19139_inspireOutputSchema().write(
            read_mcf(result), mappings_folder='ckan2pycsw/mappings')
        text = set(etree.fromstring(xml.encode()).itertext())
        self.assertTrue(urls.issubset(text))

    def test_xml_preserves_text_and_query_parameters(self):
        record = self.record()
        record.update(title='Water & soil <survey>', publisher_name='Research & Science')
        record['resources'] = [dict(name='A & B', format='CSV',
                                   url='https://example.test/download?a=1&b=2')]
        xml = ISO19139_inspireOutputSchema().write(
            read_mcf(self.convert(record)), mappings_folder='ckan2pycsw/mappings')
        root = etree.fromstring(xml.encode())
        self.assertIn(record['title'], list(root.itertext()))
        self.assertIn(record['resources'][0]['url'], list(root.itertext()))


if __name__ == '__main__':
    unittest.main()
