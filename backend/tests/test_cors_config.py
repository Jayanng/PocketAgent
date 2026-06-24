import importlib
import os
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_cors_origins_are_loaded_from_environment() -> None:
    from backend.config import get_settings
    import backend.main as main_module

    original_main_module = main_module
    custom_origin = "https://app.example.com"

    with patch.dict(
        os.environ,
        {"CORS_ORIGINS": f"{custom_origin}, http://localhost:3000"},
        clear=False,
    ):
        get_settings.cache_clear()
        reloaded = importlib.reload(main_module)
        with TestClient(reloaded.app) as client:
            response = client.options(
                "/health",
                headers={
                    "Origin": custom_origin,
                    "Access-Control-Request-Method": "GET",
                },
            )

    get_settings.cache_clear()
    importlib.reload(original_main_module)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == custom_origin
