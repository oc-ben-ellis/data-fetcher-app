"""Mock SIREN API server for testing the French INSEE API configuration.

This mock server provides endpoints that simulate the real INSEE SIREN API:
- OAuth token endpoint for authentication
- SIREN data endpoint with pagination support
- Health check endpoint
"""

import os
from datetime import datetime
from typing import Any, cast

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# Mock API responses with realistic SIREN data structure
mock_responses: dict[str, dict[str, Any]] = {
    "siren_00": {
        "total": 1500,
        "nombre": 1000,
        "curseurSuivant": "siren:01",
        "unitesLegales": [
            {
                "uniteLegale": {
                    "siren": "000000001",
                    "statutDiffusionUniteLegale": "O",
                    "dateDernierTraitementUniteLegale": "2024-01-15T10:30:00",
                    "categorieJuridiqueUniteLegale": "1000",
                    "denominationUniteLegale": "ENTREPRISE TEST 1",
                    "sigleUniteLegale": "ET1",
                    "prenomUsuelUniteLegale": None,
                    "nomUsuelUniteLegale": None,
                    "nomUsageUniteLegale": None,
                    "denominationUsuelle1UniteLegale": None,
                    "denominationUsuelle2UniteLegale": None,
                    "denominationUsuelle3UniteLegale": None,
                    "sexeUniteLegale": None,
                    "identifiantAssociationUniteLegale": None,
                    "trancheEffectifsUniteLegale": "01",
                    "anneeEffectifsUniteLegale": "2023",
                    "dateCreationUniteLegale": "2020-01-01",
                    "nombrePeriodesUniteLegale": 1,
                    "periodesUniteLegale": [
                        {
                            "dateFin": None,
                            "dateDebut": "2020-01-01",
                            "etatAdministratifUniteLegale": "A",
                            "changementEtatAdministratifUniteLegale": False,
                            "nomUniteLegale": "ENTREPRISE TEST 1",
                            "changementNomUniteLegale": False,
                            "nomUsageUniteLegale": None,
                            "changementNomUsageUniteLegale": False,
                            "denominationUsuelle1UniteLegale": None,
                            "changementDenominationUsuelle1UniteLegale": False,
                            "denominationUsuelle2UniteLegale": None,
                            "changementDenominationUsuelle2UniteLegale": False,
                            "denominationUsuelle3UniteLegale": None,
                            "changementDenominationUsuelle3UniteLegale": False,
                            "categorieJuridiqueUniteLegale": "1000",
                            "changementCategorieJuridiqueUniteLegale": False,
                            "activitePrincipaleUniteLegale": "6201Z",
                            "changementActivitePrincipaleUniteLegale": False,
                            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
                            "nicSiegeUniteLegale": "00001",
                            "changementNicSiegeUniteLegale": False,
                            "economieSocialeSolidaireUniteLegale": "N",
                            "changementEconomieSocialeSolidaireUniteLegale": False,
                            "caractereEmployeurUniteLegale": "O",
                            "changementCaractereEmployeurUniteLegale": False,
                        }
                    ],
                }
            },
            {
                "uniteLegale": {
                    "siren": "000000002",
                    "statutDiffusionUniteLegale": "O",
                    "dateDernierTraitementUniteLegale": "2024-01-15T11:30:00",
                    "categorieJuridiqueUniteLegale": "1000",
                    "denominationUniteLegale": "ENTREPRISE TEST 2",
                    "sigleUniteLegale": "ET2",
                    "prenomUsuelUniteLegale": None,
                    "nomUsuelUniteLegale": None,
                    "nomUsageUniteLegale": None,
                    "denominationUsuelle1UniteLegale": None,
                    "denominationUsuelle2UniteLegale": None,
                    "denominationUsuelle3UniteLegale": None,
                    "sexeUniteLegale": None,
                    "identifiantAssociationUniteLegale": None,
                    "trancheEffectifsUniteLegale": "02",
                    "anneeEffectifsUniteLegale": "2023",
                    "dateCreationUniteLegale": "2020-02-01",
                    "nombrePeriodesUniteLegale": 1,
                    "periodesUniteLegale": [
                        {
                            "dateFin": None,
                            "dateDebut": "2020-02-01",
                            "etatAdministratifUniteLegale": "A",
                            "changementEtatAdministratifUniteLegale": False,
                            "nomUniteLegale": "ENTREPRISE TEST 2",
                            "changementNomUniteLegale": False,
                            "nomUsageUniteLegale": None,
                            "changementNomUsageUniteLegale": False,
                            "denominationUsuelle1UniteLegale": None,
                            "changementDenominationUsuelle1UniteLegale": False,
                            "denominationUsuelle2UniteLegale": None,
                            "changementDenominationUsuelle2UniteLegale": False,
                            "denominationUsuelle3UniteLegale": None,
                            "changementDenominationUsuelle3UniteLegale": False,
                            "categorieJuridiqueUniteLegale": "1000",
                            "changementCategorieJuridiqueUniteLegale": False,
                            "activitePrincipaleUniteLegale": "6202A",
                            "changementActivitePrincipaleUniteLegale": False,
                            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
                            "nicSiegeUniteLegale": "00002",
                            "changementNicSiegeUniteLegale": False,
                            "economieSocialeSolidaireUniteLegale": "N",
                            "changementEconomieSocialeSolidaireUniteLegale": False,
                            "caractereEmployeurUniteLegale": "O",
                            "changementCaractereEmployeurUniteLegale": False,
                        }
                    ],
                }
            },
        ],
    },
    "siren_01": {
        "total": 1500,
        "nombre": 500,
        "curseurSuivant": None,
        "unitesLegales": [
            {
                "uniteLegale": {
                    "siren": "010000001",
                    "statutDiffusionUniteLegale": "O",
                    "dateDernierTraitementUniteLegale": "2024-01-15T12:30:00",
                    "categorieJuridiqueUniteLegale": "1000",
                    "denominationUniteLegale": "ENTREPRISE TEST 3",
                    "sigleUniteLegale": "ET3",
                    "prenomUsuelUniteLegale": None,
                    "nomUsuelUniteLegale": None,
                    "nomUsageUniteLegale": None,
                    "denominationUsuelle1UniteLegale": None,
                    "denominationUsuelle2UniteLegale": None,
                    "denominationUsuelle3UniteLegale": None,
                    "sexeUniteLegale": None,
                    "identifiantAssociationUniteLegale": None,
                    "trancheEffectifsUniteLegale": "03",
                    "anneeEffectifsUniteLegale": "2023",
                    "dateCreationUniteLegale": "2020-03-01",
                    "nombrePeriodesUniteLegale": 1,
                    "periodesUniteLegale": [
                        {
                            "dateFin": None,
                            "dateDebut": "2020-03-01",
                            "etatAdministratifUniteLegale": "A",
                            "changementEtatAdministratifUniteLegale": False,
                            "nomUniteLegale": "ENTREPRISE TEST 3",
                            "changementNomUniteLegale": False,
                            "nomUsageUniteLegale": None,
                            "changementNomUsageUniteLegale": False,
                            "denominationUsuelle1UniteLegale": None,
                            "changementDenominationUsuelle1UniteLegale": False,
                            "denominationUsuelle2UniteLegale": None,
                            "changementDenominationUsuelle2UniteLegale": False,
                            "denominationUsuelle3UniteLegale": None,
                            "changementDenominationUsuelle3UniteLegale": False,
                            "categorieJuridiqueUniteLegale": "1000",
                            "changementCategorieJuridiqueUniteLegale": False,
                            "activitePrincipaleUniteLegale": "6203Z",
                            "changementActivitePrincipaleUniteLegale": False,
                            "nomenclatureActivitePrincipaleUniteLegale": "NAFRev2",
                            "nicSiegeUniteLegale": "00003",
                            "changementNicSiegeUniteLegale": False,
                            "economieSocialeSolidaireUniteLegale": "N",
                            "changementEconomieSocialeSolidaireUniteLegale": False,
                            "caractereEmployeurUniteLegale": "O",
                            "changementCaractereEmployeurUniteLegale": False,
                        }
                    ],
                }
            }
        ],
    },
}


@app.route("/token", methods=["POST"])
def get_token() -> tuple[Response, int]:
    """Mock OAuth token endpoint."""
    # Check if Authorization header is present (Basic auth)
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Basic "):
        return (
            cast(
                "Response",
                jsonify(
                    {
                        "error": "invalid_request",
                        "error_description": "Missing or invalid Authorization header",
                    }
                ),
            ),
            400,
        )

    # Return a mock token response
    return (
        cast(
            "Response",
            jsonify(
                {
                    "access_token": "mock_access_token_12345",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "sirene",
                    "created_at": int(datetime.now().timestamp()),
                }
            ),
        ),
        200,
    )


@app.route("/entreprises/sirene/V3.11/siren", methods=["GET"])
def get_siren_data() -> Response | tuple[Response, int]:
    """Mock SIREN API endpoint."""
    # Extract query parameters
    q = request.args.get("q", "")

    # Check for Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return (
            cast(
                "Response",
                jsonify(
                    {
                        "error": "invalid_token",
                        "error_description": "Missing or invalid Authorization header",
                    }
                ),
            ),
            401,
        )

    # Determine which response to return based on query
    if "siren:00" in q:
        return cast("Response", jsonify(mock_responses["siren_00"]))
    if "siren:01" in q:
        return cast("Response", jsonify(mock_responses["siren_01"]))
    if "siren:99" in q:
        # Return empty response for siren:99 (end of pagination)
        return cast(
            "Response",
            jsonify(
                {"total": 0, "nombre": 0, "curseurSuivant": None, "unitesLegales": []}
            ),
        )
    # Return empty response for unknown queries
    return cast(
        "Response",
        jsonify({"total": 0, "nombre": 0, "curseurSuivant": None, "unitesLegales": []}),
    )


@app.route("/health", methods=["GET"])
def health() -> Response:
    """Health check endpoint."""
    return cast(
        "Response",
        jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "service": "siren_api_mock",
                "version": "1.0.0",
            }
        ),
    )


@app.route("/", methods=["GET"])
def root() -> Response:
    """Root endpoint with API information."""
    return cast(
        "Response",
        jsonify(
            {
                "service": "SIREN API Mock",
                "version": "1.0.0",
                "description": "Mock server for testing French INSEE API configuration",
                "endpoints": {
                    "token": "/token (POST)",
                    "siren_data": "/entreprises/sirene/V3.11/siren (GET)",
                    "health": "/health (GET)",
                },
                "documentation": "This mock server simulates the INSEE SIREN API for testing purposes",
            }
        ),
    )


@app.errorhandler(404)
def not_found(error: Any) -> tuple[Response, int]:
    """Handle 404 errors."""
    return (
        cast(
            "Response",
            jsonify({"error": "not_found", "error_description": "Endpoint not found"}),
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error: Any) -> tuple[Response, int]:
    """Handle 500 errors."""
    return (
        cast(
            "Response",
            jsonify(
                {
                    "error": "internal_server_error",
                    "error_description": "Internal server error",
                }
            ),
        ),
        500,
    )


if __name__ == "__main__":
    # Get port from environment or default to 5000
    port = int(os.environ.get("PORT", 5000))

    # Run the Flask app
    app.run(host="0.0.0.0", port=port, debug=True)
