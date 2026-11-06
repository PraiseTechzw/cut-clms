def test_healthz_reports_ok_and_service_identity(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/healthz")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "CUT-CLMS API"
    assert payload["environment"] == "test"


def test_readyz_returns_ok_when_database_reachable(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz_returns_503_when_database_unreachable(client, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from sqlalchemy.exc import OperationalError

    def broken_database(engine):  # type: ignore[no-untyped-def]
        raise OperationalError("connection failed", None, Exception("boom"))

    monkeypatch.setattr("cut_clms_api.main.check_database", broken_database)

    response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["error"]["message"] == "database not ready"


def test_root_redirects_to_api_documentation(client) -> None:  # type: ignore[no-untyped-def]
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"
