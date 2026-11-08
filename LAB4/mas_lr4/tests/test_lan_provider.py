"""The explicitly configured LAN endpoint is available to every architecture."""
import unittest
from unittest.mock import patch
from maslab.provider import HTTPProvider, ProviderError


class LANProviderTests(unittest.TestCase):
    def test_lan_endpoint(self):
        with patch.dict('os.environ', {'MAS_LLM_BASE_URL': 'http://192.168.3.42:8000/v1'}):
            provider = HTTPProvider({'model': 'fixture'})
        self.assertEqual(provider.url, 'http://192.168.3.42:8000/v1/chat/completions')

    def test_other_remote_http_still_rejected(self):
        with patch.dict('os.environ', {'MAS_LLM_BASE_URL': 'http://example.com/v1'}):
            with self.assertRaises(ProviderError):
                HTTPProvider({'model': 'fixture'})
