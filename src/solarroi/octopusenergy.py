import logging
import requests

from typing import Dict
from solarroi.common import get_config_opion

BASE_URL = "https://api.octopus.energy/v1"
CONFIG_SECTION = "OctopusEnergy"

__url_cache = {}

def get_account() -> str:
    return get_config_opion(CONFIG_SECTION, "account")


def get_api_key() -> str:
    return get_config_opion(CONFIG_SECTION, "api_key")


def get_export_meter_mpan() -> str:
    return get_config_opion(CONFIG_SECTION, "export_meter_mpan")


def get_export_meter_serial() -> str:
    return get_config_opion(CONFIG_SECTION, "export_meter_serial")


def get_export_product_code() -> str:
    return get_config_opion(CONFIG_SECTION, "export_product_code")


def get_export_tariff_code() -> str:
    return get_config_opion(CONFIG_SECTION, "export_tariff_code")


def get_import_meter_mpan() -> str:
    return get_config_opion(CONFIG_SECTION, "import_meter_mpan")


def get_import_meter_serial() -> str:
    return get_config_opion(CONFIG_SECTION, "import_meter_serial")


def get_import_tariff_code() -> str:
    return get_config_opion(CONFIG_SECTION, "import_tariff_code")


def get_import_product_code() -> str:
    return get_config_opion(CONFIG_SECTION, "import_product_code")


def get_export_energy_generated_by_day(
    start_date: str, end_date: str
) -> Dict[str, float]:
    return get_energy_consumption_by_day(
        start_date, end_date, get_export_meter_mpan(), get_export_meter_serial()
    )


def get_import_energy_use_by_day(
    start_date: str, end_date: str
) -> Dict[str, float]:
    return get_energy_consumption_by_day(
        start_date, end_date, get_import_meter_mpan(), get_import_meter_serial()
    )


def get_energy_consumption_by_day(
    start_date: str,
    end_date: str,
    mpan: str,
    serial: str
) -> Dict[str, float]:
    api_key = get_api_key()

    url = f"{BASE_URL}/electricity-meter-points/{mpan}/meters/{serial}/consumption/"

    params = {
        "period_from": f"{start_date}T00:00:00Z",
        "period_to": f"{end_date}T00:00:00Z",
        "group_by": "day",
        "order_by": "period"
    }

    response = requests.request("GET", url, auth=(api_key, ""), params=params)
    data = response.json()

    results = {}

    for data_point in data["results"]:
        date = data_point["interval_start"][0:10]
        results[date] = data_point["consumption"]

    return results


def get_export_tariff_cost(date: str) -> float:
    export_product_code = get_export_product_code()
    export_tariff_code = get_export_tariff_code()
    return get_tariff_cost(date, export_tariff_code, export_product_code)


def get_import_tariff_cost(date: str) -> float:
    import_product_code = get_import_product_code()
    import_tariff_code = get_import_tariff_code()
    return get_tariff_cost(date, import_tariff_code, import_product_code)


def get_tariff_cost(
    date: str, tariff_code: str, product_code: str
) -> float:
    date = f"{date}T00:00:00Z"
    url = f"{BASE_URL}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/"

    if url not in __url_cache:
        response = requests.request("GET", url)
        __url_cache[url] = response.json()
    else:
        logging.debug("get_tariff_cost: using cache for %s", url)

    data = __url_cache[url]

    for data_point in data["results"]:
        if data_point["payment_method"] is None or data_point["payment_method"] == "DIRECT_DEBIT":
            if date > data_point["valid_from"] and (data_point["valid_to"] is None or date < data_point["valid_to"]):
                # convert from pence to pounds
                return float(data_point["value_inc_vat"]) / 100
    logging.error("Could not find unit cost for %s", url)
    return 0
