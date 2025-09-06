"""Simple mock HTTP server for functional tests.

This module provides a simple HTTP server that can be used instead of
Mockoon for functional tests when Docker is not available or working properly.
"""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


class MockAPIHandler(BaseHTTPRequestHandler):
    """Handler for mock API requests."""

    def do_GET(self) -> None:
        """Handle GET requests."""
        if self.path == "/health":
            self._send_json_response(
                200,
                {
                    "service": "siren_api_mock",
                    "status": "healthy",
                    "timestamp": "2025-09-07T10:00:00.000Z",
                    "version": "1.0.0",
                },
            )
        elif self.path.startswith("/entreprises/sirene/V3.11/siren"):
            self._send_json_response(
                200,
                {
                    "header": {
                        "statut": 200,
                        "message": "OK",
                        "total": 1,
                        "debut": 1,
                        "nombre": 1,
                    },
                    "unitesLegales": [
                        {
                            "siren": "123456789",
                            "statutDiffusionUniteLegale": "O",
                            "dateCreationUniteLegale": "2020-01-01",
                            "sigleUniteLegale": "TEST",
                            "denominationUniteLegale": "TEST COMPANY",
                            "denominationUsuelle1UniteLegale": "TEST",
                            "categorieJuridiqueUniteLegale": "5710",
                            "activitePrincipaleUniteLegale": "62.01Z",
                            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
                            "caractereEmployeurUniteLegale": "O",
                            "trancheEffectifsUniteLegale": "00",
                            "effectifMinUniteLegale": 0,
                            "effectifMaxUniteLegale": 0,
                            "dateDernierTraitementUniteLegale": "2025-09-07T10:00:00",
                            "etablissements": [
                                {
                                    "siren": "123456789",
                                    "siret": "12345678900001",
                                    "dateCreationEtablissement": "2020-01-01",
                                    "codePostalEtablissement": "75001",
                                    "libelleCommuneEtablissement": "PARIS 1ER",
                                    "codeCommuneEtablissement": "75101",
                                    "activitePrincipaleEtablissement": "62.01Z",
                                    "nomenclatureActivitePrincipaleEtablissement": "NAFRev2",
                                    "caractereEmployeurEtablissement": "O",
                                    "trancheEffectifsEtablissement": "00",
                                    "effectifMinEtablissement": 0,
                                    "effectifMaxEtablissement": 0,
                                    "dateDernierTraitementEtablissement": "2025-09-07T10:00:00",
                                }
                            ],
                        }
                    ],
                    "curseurSuivant": None,
                },
            )
        else:
            self._send_json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        """Handle POST requests."""
        if self.path == "/token":
            self._send_json_response(
                200,
                {
                    "access_token": "mock_access_token_12345",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                },
            )
        else:
            self._send_json_response(404, {"error": "Not found"})

    def _send_json_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Send a JSON response."""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def log_message(self, format_str: str, *args: Any) -> None:
        """Suppress log messages."""


class SimpleMockServer:
    """Simple mock HTTP server for testing."""

    def __init__(self, host: str = "localhost", port: int = 0) -> None:
        """Initialize the mock server.

        Args:
            host: Host to bind to.
            port: Port to bind to. If 0, use a random available port.
        """
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the mock server."""
        self.server = HTTPServer((self.host, self.port), MockAPIHandler)
        # Get the actual port if we used 0 (random port)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        time.sleep(0.1)  # Give server time to start

    def stop(self) -> None:
        """Stop the mock server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self.thread:
            self.thread.join(timeout=1.0)

    def is_running(self) -> bool:
        """Check if the server is running."""
        try:
            import urllib.request

            urllib.request.urlopen(f"http://{self.host}:{self.port}/health", timeout=1)
            return True
        except Exception:
            return False
