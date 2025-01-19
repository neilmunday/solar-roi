import logging
import requests

from typing import Any, Dict
from solarroi.common import get_config_opion

CONFIG_SECTION = "Solcast"


def get_api_key() -> str:
    return get_config_opion(CONFIG_SECTION, "api_key")


def get_resource_id() -> str:
    return get_config_opion(CONFIG_SECTION, "resource_id")


def get_forecasts() -> Dict[str, Any]:
    api_key = get_api_key()
    resource_id = get_resource_id()

    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"https://api.solcast.com.au/rooftop_sites/{resource_id}/forecasts?format=json"

    result = requests.get(url, headers=headers)

    if result.status_code != 200:
        logging.error("%s returned: %d", url, result.status_code)

    result_json = result.json()

    if "forecasts" not in result_json:
        raise RuntimeError("forecasts missing in solcast API response")

    return result_json["forecasts"]
