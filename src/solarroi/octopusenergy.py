import datetime
import logging
import requests

from typing import Any, Dict, List, Optional
from solarroi.common import get_config_opion, get_datetime_from_date

BASE_URL = "https://api.octopus.energy/v1"
CONFIG_SECTION = "OctopusEnergy"


class TarrifPeriod:

    def __init__(self, valid_from: datetime.datetime, valid_to: datetime.datetime, price: float):
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.price = price / 100  # convert to pounds

    def __repr__(self) -> str:
        return f"<valid_from {self.valid_from.isoformat()}, valid_to: {self.valid_to.isoformat()}, price: {self.price}>"

    def is_active(self, dt: datetime.datetime) -> bool:
        return dt >= self.valid_from and dt <= self.valid_to


class Meter:

    def __init__(
        self, is_export: bool, mpan: str, serial: str, agrements: Any
    ):
        self.is_export = is_export
        self.mpan = mpan
        self.serial = serial
        self.agreements = agrements

    def __repr__(self) -> str:
        return f"<mpan: {self.mpan}, serial: {self.serial}, export: {self.is_export}, agreements: {self.agreements} >"


def get_account() -> str:
    return get_config_opion(CONFIG_SECTION, "account")


def get_api_key() -> str:
    return get_config_opion(CONFIG_SECTION, "api_key")


def get_tariff_history() -> tuple[Optional[Meter], Optional[Meter]]:
    url = f"{BASE_URL}/accounts/{get_account()}/"
    response = load_url(url)
    import_meter = None
    export_meter = None
    for meter_point in response["properties"][0]["electricity_meter_points"]:
        if meter_point["is_export"]:
            export_meter = Meter(
                True,
                meter_point["mpan"],
                meter_point["meters"][0]["serial_number"],
                meter_point["agreements"]
            )
        else:
            import_meter = Meter(
                False,
                meter_point["mpan"],
                meter_point["meters"][0]["serial_number"],
                meter_point["agreements"]
            )
    return (import_meter, export_meter)


def load_url(url: str, params: Optional[Dict] = None) -> Any:
    logging.debug("load_url: %s", url)
    response = requests.request(
        "GET", url, auth=(get_api_key(), ""), params=params
    )
    return response.json()


def get_energy_cost_by_day(
    meter: Meter, start_date_str: str, end_date_str: str
) -> Dict:
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)

    logging.debug("get_energy_cost_by_day: %s to %s", start_date, end_date)

    costs: Dict[str, float] = {}
    consumption: Dict[str, float] = {}
    prices: Dict[str, List[TarrifPeriod]] = {}

    current_date = start_date
    while current_date <= end_date:
        logging.debug("get_energy_cost_by_day: day = %s", current_date)
        next_date = current_date + datetime.timedelta(days=1)
        prev_date = current_date - datetime.timedelta(days=1)
        current_date_iso = current_date.isoformat()
        next_date_iso = next_date.isoformat()
        prev_date_iso = prev_date.isoformat()
        current_date_time = get_datetime_from_date(current_date)
        next_date_time = get_datetime_from_date(next_date)
        tariff_code = None
        cost = 0.0
        agreements_total = len(meter.agreements)
        # get tariff for this day
        for index, agreement in enumerate(meter.agreements):
            logging.debug("get_energy_cost_by_day: agreement = %s", agreement)
            if (
                (
                    current_date_iso >= agreement["valid_from"] and (
                        agreement["valid_to"] is None
                        or current_date_iso < agreement["valid_to"]
                    )
                ) or (
                    # hack for Ocotpus Energy bug where valid_to is wrong
                    current_date_iso >= agreement["valid_from"] and
                    index == agreements_total - 1
                )
            ):
                tariff_code = agreement["tariff_code"]
                parts = tariff_code.split("-")
                product_code = "-".join(parts[2:-1])
                logging.debug(
                    "get_energy_cost_by_day: %s = %s, %s",
                    current_date,
                    product_code,
                    tariff_code
                )
                break

        if tariff_code is None:
            logging.warning("Could not determine tariff code for %s for meter %s", current_date_iso, meter.mpan)
            costs[current_date_iso] = 0.0
            prices[current_date_iso] = [TarrifPeriod(current_date_time, next_date_time, 0.0)]
        else:
            prices[current_date_iso] = []

            # get prices for the day
            prices_for_day = load_url(
                f"{BASE_URL}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
                {
                    "period_from": current_date_iso,
                    "period_to": next_date_iso
                }
            )

            if prices_for_day["count"] < 1:
                logging.error("No prices for: %s", current_date)
            else:
                for price_result in prices_for_day["results"]:
                    url = f"{BASE_URL}/electricity-meter-points/{meter.mpan}/meters/{meter.serial}/consumption/"

                    valid_from = ""
                    valid_to = ""

                    if (
                        current_date_iso not in price_result["valid_from"] and
                        prev_date_iso not in price_result["valid_from"]
                    ):
                        valid_from = get_datetime_from_date(current_date).isoformat()
                    else:
                        valid_from = price_result["valid_from"]

                    if price_result["valid_to"] is None or current_date_iso not in price_result["valid_to"]:
                        valid_to = get_datetime_from_date(current_date, True).isoformat()
                    else:
                        valid_to = (
                            datetime.datetime.fromisoformat(price_result["valid_to"]) - datetime.timedelta(seconds=1)
                        ).isoformat()

                    prices[current_date_iso].append(
                        TarrifPeriod(
                            datetime.datetime.fromisoformat(valid_from),
                            datetime.datetime.fromisoformat(valid_to),
                            price_result["value_inc_vat"],
                        )
                    )

                    params = {
                        "period_from": valid_from,
                        "period_to": valid_to,
                        "group_by": "day",
                        "order_by": "period"
                    }

                    consumption_data = load_url(
                        url,
                        params
                    )

                    if consumption_data["count"] > 0:
                        for consumption_result in consumption_data["results"]:
                            interval_start_dt = datetime.date.fromisoformat(consumption_result["interval_start"][0:10])
                            if interval_start_dt == current_date:
                                cost += consumption_result["consumption"] * price_result["value_inc_vat"]
                                if current_date in consumption:
                                    consumption[current_date_iso] += consumption_result["consumption"]
                                else:
                                    consumption[current_date_iso] = consumption_result["consumption"]

        cost = round(cost / 100, 2)
        costs[current_date_iso] = cost

        current_date += datetime.timedelta(days=1)

    if meter.is_export:
        result = {
            "prices": prices,
            "generation": consumption,
            "income": costs
        }
    else:
        result = {
            "prices": prices,
            "consumption": consumption,
            "expenditure": costs
        }

    logging.debug("get_energy_cost_by_day: returning %s", result)

    return result


def get_energy_cost_by_day_orig(
    meter: Meter, start_date_str: str, end_date_str: str
) -> Dict:
    start_date = datetime.date.fromisoformat(start_date_str)
    end_date = datetime.date.fromisoformat(end_date_str)

    logging.debug("get_energy_cost_by_day: %s to %s", start_date, end_date)

    costs = {}
    consumption = {}
    prices = {}

    logging.debug(
        "get_energy_cost_by_day: meter (%s, %s, %s)",
        meter.mpan,
        meter.serial,
        meter.is_export
    )

    url = f"{BASE_URL}/electricity-meter-points/{meter.mpan}/meters/{meter.serial}/consumption/"
    params = {
        "period_from": f"{start_date}T00:00:00Z",
        "period_to": f"{end_date}T00:00:00Z",
        "group_by": "day",
        "order_by": "period"
    }

    while True:
        consumption_data = load_url(
            url,
            params
        )

        for data_point in consumption_data["results"]:
            date = data_point["interval_start"][0:10]
            consumption[date] = data_point["consumption"]

        if "next" in consumption_data and consumption_data["next"] is not None:
            url = consumption_data["next"]
        else:
            logging.debug("get_energy_cost_by_day: end of data points")
            break

    current_date = start_date
    while current_date <= end_date:
        logging.debug("get_energy_cost_by_day: day = %s", current_date)
        next_date = current_date + datetime.timedelta(days=1)
        current_date_iso = current_date.isoformat()
        next_date_iso = next_date.isoformat()
        tariff_code = None
        # get tariff for this day
        for agreement in meter.agreements:
            if current_date_iso >= agreement["valid_from"] and current_date_iso < agreement["valid_to"]:
                tariff_code = agreement["tariff_code"]
                parts = tariff_code.split("-")
                product_code = "-".join(parts[2:-1])
                logging.debug(
                    "get_energy_cost_by_day: %s = %s, %s",
                    current_date,
                    product_code,
                    tariff_code
                )
                break

        if tariff_code is None:
            logging.warning("Could not determine tariff code for %s for meter %s", current_date_iso, meter.mpan)
            costs[current_date_iso] = 0.0
            prices[current_date_iso] = 0.0
        else:
            # get prices for the day
            prices_for_day = load_url(
                f"{BASE_URL}/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
                {
                    "period_from": current_date_iso,
                    "period_to": next_date_iso
                }
            )

            if prices_for_day["count"] == 1:
                # convert from pence to pounds
                prices[current_date_iso] = float(prices_for_day["results"][0]["value_inc_vat"]) / 100
            elif prices_for_day["count"] > 1:
                # find DD value
                for result in prices_for_day["results"]:
                    if result["payment_method"] == "DIRECT_DEBIT":
                        # convert from pence to pounds
                        prices[current_date_iso] = float(result["value_inc_vat"]) / 100
            else:
                raise Exception(f"Could not deterimine prices for {current_date_iso}")

            if current_date_iso in consumption:
                costs[current_date_iso] = round(prices[current_date_iso] * consumption[current_date_iso], 2)

        current_date += datetime.timedelta(days=1)

    if meter.is_export:
        result = {
            "prices": prices,
            "generation": consumption,
            "income": costs
        }
    else:
        result = {
            "prices": prices,
            "consumption": consumption,
            "expenditure": costs
        }

    logging.debug("get_energy_cost_by_day: returning %s", result)

    return result
