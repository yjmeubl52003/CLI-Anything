"""Live integration tests for ACE Studio MCP."""

from __future__ import annotations

import unittest
from urllib import request

from cli_anything.acestudio.core import project, track
from cli_anything.acestudio.mcp_client import ACEStudioMCPClient, DEFAULT_MCP_URL


def _mcp_available() -> bool:
    req = request.Request(DEFAULT_MCP_URL, method="OPTIONS")
    try:
        with request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


@unittest.skipUnless(_mcp_available(), "ACE Studio MCP server is not available")
class LiveIntegrationTests(unittest.TestCase):
    def test_initialize_live_session(self):
        client = ACEStudioMCPClient(timeout=5)
        result = client.initialize()
        self.assertTrue(result["protocolVersion"])
        self.assertTrue(client.session_id)

    def test_project_info_live(self):
        client = ACEStudioMCPClient(timeout=5)
        result = project.get_info(client)
        self.assertIn("duration_ticks", result)

    def test_track_clear_selection_live(self):
        client = ACEStudioMCPClient(timeout=5)
        result = track.clear_selected_tracks(client)
        self.assertEqual(result["selected_track_indices"], [])


if __name__ == "__main__":
    unittest.main()
