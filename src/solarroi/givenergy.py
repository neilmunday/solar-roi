import datetime
import logging
import requests

from enum import Enum
from typing import Any, Dict

from solarroi.common import get_config_opion, die

logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

BASE_URL = "https://api.givenergy.cloud/v1"
CONFIG_SECTION = "GivEnergy"


class ConsumptionPeriod:

    def __init__(self, valid_from: datetime.datetime, valid_to: datetime.datetime, consumption: float):
        self.valid_from = valid_from.astimezone(datetime.timezone.utc)
        self.valid_to = valid_to.astimezone(datetime.timezone.utc)
        self.consumption = consumption

    def __repr__(self) -> str:
        return f"<valid_from {self.valid_from.isoformat()}, valid_to: {self.valid_to.isoformat()}, consumption: {self.consumption}>"


class GroupingType(Enum):
    HALF_HOUR = 0
    DAILY = 1
    MONTHLY = 2
    YEARLY = 3
    TOTAL = 4


class EnergyType(Enum):
    PV_TO_HOME = 0
    PV_TO_BATTERY = 1
    PV_TO_GRID = 2
    GRID_TO_HOME = 3
    GRID_TO_BATTERY = 4
    BATTERY_TO_HOME = 5
    BATTERY_TO_GRID = 6


def check_response(data: Dict[str, str]):
    if "message" in data and data["message"] == "Too Many Attempts.":
        die("Too many GivEnergy API requests!")


def get_api_key() -> str:
    return get_config_opion(CONFIG_SECTION, "api_key")


def get_energy_consumption_by_day(start_date: str, end_date: str):
    api_key = get_api_key()
    inverter_serial = get_inverter_serial()

    home_consumption_types = [
        EnergyType.BATTERY_TO_HOME.value,
        EnergyType.GRID_TO_HOME.value,
        EnergyType.PV_TO_HOME.value
    ]

    grid_import_types = [
        EnergyType.GRID_TO_BATTERY.value,
        EnergyType.GRID_TO_HOME.value
    ]

    types_array = home_consumption_types + grid_import_types

    url = f"{BASE_URL}/inverter/{inverter_serial}/energy-flows"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    params = {
        "start_time": start_date,
        "end_time": end_date,
        "grouping": GroupingType.HALF_HOUR.value,
        "types": types_array
    }

    response = requests.request('POST', url, headers=headers, json=params)
    data = response.json()

    check_response(data)

    results: Dict[str, Any] = {}

    if "message" in data and "Unauthenticated" in data["message"]:
        raise RuntimeError("Unable to access GivEnergy API: Unauthenticated")

    for data_point in data["data"].values():
        date = data_point["start_time"][0:10]
        # sum up energy usage
        home_consumption = 0
        grid_import = 0

        for key, value in data_point["data"].items():
            if int(key) in grid_import_types:
                grid_import += value
            if int(key) in home_consumption_types:
                home_consumption += value

        if date not in results:
            results[date] = {
                "total_grid_import": grid_import,
                "total_home_consumption": home_consumption,
                "consumption_periods": [ConsumptionPeriod(
                    datetime.datetime.fromisoformat(data_point["start_time"]),
                    datetime.datetime.fromisoformat(data_point["end_time"]),
                    home_consumption
                )]
            }
        else:
            results[date]["total_grid_import"] += grid_import
            results[date]["total_home_consumption"] += home_consumption
            results[date]["consumption_periods"].append(
                ConsumptionPeriod(
                    datetime.datetime.fromisoformat(data_point["start_time"]),
                    datetime.datetime.fromisoformat(data_point["end_time"]),
                    home_consumption
                )
            )

        results[date]["total_grid_import"] = round(results[date]["total_grid_import"], 2)
        results[date]["total_home_consumption"] = round(results[date]["total_home_consumption"], 2)

    return results


def get_meter_total_consumption(date: str):
    logging.debug("Getting total consumption for %s", date)
    iso_date = f"{date}T23:59:00Z"
    api_key = get_api_key()
    inverter_serial = get_inverter_serial()
    logging.debug("Fecthing data for inveter: %s", inverter_serial)

    url = f"{BASE_URL}/inverter/{inverter_serial}/data-points/{iso_date}"

    # load first page
    first_page_data = load_page(url, 1, api_key)
    # work out the last page of data
    last_page = int(first_page_data["meta"]["last_page"])
    last_page_data = load_page(url, last_page, api_key)
    last_data_point = last_page_data["data"][-1]
    last_data_point_time = last_data_point["time"]

    if not last_data_point["time"].startswith(date):
        die(f"Unexpected data point for {last_data_point_time}")

    return last_data_point["today"]["consumption"]


def get_inverter_serial() -> str:
    return get_config_opion(CONFIG_SECTION, "inverter_serial")


def load_page(url: str, page: int, api_key: str) -> Dict:
    params = {
        "page": page
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    response = requests.request("GET", url, headers=headers, params=params)
    data = response.json()
    check_response(data)
    return data
