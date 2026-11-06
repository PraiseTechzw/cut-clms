def test_openapi_schema_exposes_health_paths(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()

    assert set(schema["paths"]) == {"/healthz", "/readyz"}
    assert schema["components"]["schemas"]["HealthResponse"]["properties"]["status"]["enum"] == ["ok"]
    assert schema["components"]["schemas"]["ReadinessResponse"]["properties"]["status"]["enum"] == ["ok"]
    assert schema["components"]["schemas"]["ReadinessFailure"]["properties"]["status"]["enum"] == ["unavailable"]


def test_openapi_schema_stable_field_dump() -> None:  # type: ignore[no-untyped-def]
    from cut_clms_api.openapi_export import build_schema

    schema = build_schema()

    assert schema["info"]["title"] == "CUT-CLMS API"
