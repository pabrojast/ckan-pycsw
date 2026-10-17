import importlib.util
import pathlib
import signal
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('refresh', pathlib.Path(__file__).resolve().parents[1] / 'ckan2pycsw/ckan2pycsw.py')
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


class RefreshTests(unittest.TestCase):
    def test_failed_harvest_keeps_previous_database(self):
        with tempfile.TemporaryDirectory() as directory:
            live = pathlib.Path(directory) / 'live.db'
            live.write_bytes(b'previous database')
            def interrupted():
                raise RuntimeError('CKAN unavailable')
                yield
            with self.assertRaisesRegex(RuntimeError, 'CKAN unavailable'):
                refresh.build_catalogue('sqlite:///' + str(live), 'records', interrupted())
            self.assertEqual(live.read_bytes(), b'previous database')
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [live])

    def test_empty_harvest_keeps_previous_database(self):
        with tempfile.TemporaryDirectory() as directory:
            live = pathlib.Path(directory) / 'live.db'
            live.write_bytes(b'previous database')
            with self.assertRaisesRegex(RuntimeError, 'zero records'):
                refresh.build_catalogue('sqlite:///' + str(live), 'records', iter(()))
            self.assertEqual(live.read_bytes(), b'previous database')

    def test_failed_refresh_does_not_touch_server(self):
        with patch.object(refresh, 'main', side_effect=RuntimeError('conversion failed')), \
                patch.object(refresh.psutil, 'Process') as process, \
                patch.object(refresh.subprocess, 'Popen') as launch:
            with self.assertRaises(RuntimeError):
                refresh.run_tasks()
            process.assert_not_called()
            launch.assert_not_called()

    def test_successful_refresh_gracefully_reloads_master(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(refresh, 'APP_DIR', directory), \
                patch.object(refresh, 'main') as rebuild, \
                patch.object(refresh.psutil, 'Process') as process, \
                patch.object(refresh.subprocess, 'Popen') as launch:
            (pathlib.Path(directory) / 'gunicorn.pid').write_text('123')
            process.return_value.cmdline.return_value = ['gunicorn: master']
            refresh.run_tasks()
            rebuild.assert_called_once()
            process.return_value.send_signal.assert_called_once_with(signal.SIGHUP)
            launch.assert_not_called()

    def test_pagination_fails_on_partial_response(self):
        response = Mock()
        response.json.side_effect = [
            {'success': True, 'result': {'count': 2, 'results': [{'id': 'a', 'type': 'dataset'}]}},
            {'success': True, 'result': {'count': 2, 'results': []}},
        ]
        with patch.object(refresh.requests, 'get', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'incomplete page'):
                list(refresh.get_datasets('https://example.test/'))

    def test_private_dataset_is_never_published(self):
        response = Mock()
        response.json.return_value = {'success': True, 'result': {
            'count': 1, 'results': [{'id': 'private', 'type': 'dataset', 'private': True}]}}
        with patch.object(refresh.requests, 'get', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'private dataset'):
                list(refresh.get_datasets('https://example.test/'))
