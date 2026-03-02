import unittest
from unittest import mock
import urllib.error

from server.plugins import ScryfallPlugin


class ScryfallPluginTest(unittest.TestCase):
    def test_exact_fetch_handles_url_error(self):
        plugin = ScryfallPlugin()
        with mock.patch.object(plugin, '_open_json', side_effect=urllib.error.URLError('boom')):
            stream, meta = plugin.Fetch('Black Lotus', True, 20)

        self.assertEqual(stream, [])
        self.assertEqual(meta, {'has_more': False, 'more_url': ''})

    def test_search_fetch_handles_http_error(self):
        plugin = ScryfallPlugin()
        with mock.patch.object(plugin, '_open_json', side_effect=urllib.error.HTTPError(
            url='https://api.scryfall.com/cards/search?q=lotus',
            code=429,
            msg='rate limited',
            hdrs=None,
            fp=None,
        )):
            stream, meta = plugin.Fetch('Lotus', False, 20)

        self.assertEqual(stream, [])
        self.assertEqual(meta, {'has_more': False, 'more_url': ''})


if __name__ == '__main__':
    unittest.main()
