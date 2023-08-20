import argparse
import datetime
import logging
import pathlib
import re

import solarroi
import solarroi.givenergy as givenergy
import solarroi.octopusenergy as octopus_energy

from solarroi.common import check_file, die
from solarroi.sql import connect_db, SolarROI


def main():
    parser = argparse.ArgumentParser(
        description="Calculate ROI for your PV system using GivEnergy " +
                    "and Octopus Energy APIs",
        add_help=True
    )
    parser.add_argument(
        "-c", "--config", help="Path to config file",
        dest="config_path"
    )
    parser.add_argument(
        "-d", "--use-database", help="Save records to database",
        dest="use_database", action="store_true"
    )
    parser.add_argument(
        "-s", "--start", help="Date to get consumption data from. Use now-X " +
                              "to specify a date X days ago.",
        dest="start_date", required=True
    )
    parser.add_argument(
        "-v", "--verbose", help="Turn on debug messages", dest="verbose",
        action="store_true"
    )

    args = parser.parse_args()

    log_date = "%Y/%m/%d %H:%M:%S"
    log_format = "%(asctime)s:%(levelname)s: %(message)s"
    log_level = logging.INFO
    if args.verbose:
        log_level = logging.DEBUG

    logging.basicConfig(format=log_format, datefmt=log_date, level=log_level)

    if args.config_path:
        config_path = pathlib.Path(args.config_path).resolve()
        logging.debug("Using config file: %s", config_path)
        check_file(config_path)
        solarroi.conf_file = config_path

    today = datetime.datetime.now().date()
    today_str = str(today)

    # Check start date argument
    now_re = re.compile(r"^now-(?P<days>[0-9])+$")
    date_re = re.compile(r"^2[0-9]{3}-[0|1|2][0-9]-[0|1|2|3][0-9]+$")

    start_date = args.start_date

    now_match = now_re.match(start_date)
    if now_match:
        minus_days = int(now_match.group("days"))
        start_date = str(today - datetime.timedelta(days=minus_days))
    else:
        if not date_re.match(start_date):
            die(f"Invalid start date: {args.start_date}")

    results = {}
    roi = 0

    logging.debug("Querying GivEnergy API")

    giv_energy_use = givenergy.get_energy_consumption_by_day(
        start_date,
        today_str
    )

    for date, result in giv_energy_use.items():
        no_pv_cost = round(
            octopus_energy.get_import_tariff_cost(date) * result["home_consumption"], 2
        )
        results[date] = {
            "home_consumption": result["home_consumption"],
            "no_pv_cost": no_pv_cost
        }

    logging.debug("Querying Octopus Energy API")

    octopus_energy_use = octopus_energy.get_import_energy_use_by_day(
        start_date,
        today_str
    )

    for date, value in octopus_energy_use.items():
        if date in results:
            results[date]["grid_import"] = value
            results[date]["cost"] = round(
                value * octopus_energy.get_import_tariff_cost(date), 2
            )
            results[date]["grid_export"] = 0
            results[date]["income"] = 0
            results[date]["roi"] = results[date]["no_pv_cost"] - results[date]["cost"]
            roi += results[date]["roi"]

    octopus_energy_export = octopus_energy.get_export_energy_generated_by_day(
        start_date,
        today_str
    )

    for date, value in octopus_energy_export.items():
        if date in results:
            results[date]["grid_export"] = value
            results[date]["income"] = round(
                value * octopus_energy.get_export_tariff_cost(date), 2
            )
            results[date]["roi"] += results[date]["income"]
            roi += results[date]["income"]

    logging.debug(results)
    days = len(results)
    roi_per_day = round(roi / days, 2)

    print(f"ROI: £{round(roi, 2)} for {days} days")
    print(f"ROI per day: £{roi_per_day}")

    if args.use_database:
        logging.debug("Saving records to database...")
        session_maker = connect_db()
        with session_maker() as session:
            for date, record in results.items():
                fields_missing = []
                for field in ["cost", "grid_export", "grid_import",
                              "home_consumption", "income", "no_pv_cost",
                              "roi"]:
                    if field not in record:
                        fields_missing.append(field)

                if len(fields_missing) > 0:
                    logging.warning("Missing fields: %s", ",".join(
                        fields_missing
                    ))
                    continue

                solar_roi = session.query(SolarROI).filter(
                    SolarROI.date == date
                ).first()
                if solar_roi:
                    logging.debug("Updating existing record for %s", date)
                    solar_roi.cost = record["cost"]
                    solar_roi.grid_export = record["grid_export"]
                    solar_roi.grid_import = record["grid_import"]
                    solar_roi.home_consumption = record["home_consumption"]
                    solar_roi.income = record["income"]
                    solar_roi.no_pv_cost = record["no_pv_cost"]
                    solar_roi.roi = record["roi"]
                else:
                    logging.debug("Creating new record for %s", date)
                    solar_roi = SolarROI(
                        date=date,
                        cost=record["cost"],
                        grid_export=record["grid_export"],
                        grid_import=record["grid_import"],
                        home_consumption=record["home_consumption"],
                        income=record["income"],
                        no_pv_cost=record["no_pv_cost"],
                        roi=record["roi"]
                    )
                session.add(solar_roi)
                session.commit()
        logging.debug("Database update complete")    
