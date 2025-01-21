import argparse
import datetime
import logging
import pathlib
import pprint
import re

import solarroi
import solarroi.givenergy as givenergy
import solarroi.octopusenergy as octopus_energy
import solarroi.solcast as solcast

from solarroi.common import check_file, die
from solarroi.sql import connect_db, Solcast, SolarROI


def solar_forecast_main():
    parser = argparse.ArgumentParser(
        description="Fetch solar forecast from Solcast",
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

    forecasts = solcast.get_forecasts()

    if len(forecasts) == 0:
        die("No forecast records returned!")

    if args.use_database:
        logging.debug("Saving records to database...")
        session_maker = connect_db()
        with session_maker() as session:
            for forecast in forecasts:
                date = datetime.datetime.fromisoformat(forecast["period_end"])
                pv_estimate = forecast["pv_estimate"]

                forecast_record = session.query(Solcast).filter(
                    Solcast.date == date
                ).first()

                if forecast_record:
                    logging.debug("Updating existing record for %s", date)
                    forecast_record.pv_estimate = pv_estimate
                else:
                    logging.debug("Creating new record for %s", )

                    forecast_record = Solcast(
                        date=date,
                        pv_estimate=pv_estimate
                    )

                session.add(forecast_record)
                session.commit()

        logging.info("Forecast records saved to database")
    else:
        pprint.pprint(forecasts)


def solar_roi_main():
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
        "-e", "--end", help="End date to get consumption data up to.",
        dest="end_date", required=False
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

    date_re = re.compile(r"^2[0-9]{3}-[0|1|2][0-9]-[0|1|2|3][0-9]+$")

    end_date = None

    if args.end_date is not None:
        if not date_re.match(args.end_date):
            die(f"Invalid end date: {args.end_date}")
        end_date = args.end_date
    else:
        today = datetime.datetime.now().date()
        end_date = str(today)

    # Check start date argument
    now_re = re.compile(r"^now-(?P<days>[0-9]+)$")

    start_date = args.start_date

    now_match = now_re.match(start_date)
    if now_match:
        minus_days = int(now_match.group("days"))
        start_date = str(today - datetime.timedelta(days=minus_days))
    else:
        if not date_re.match(start_date):
            die(f"Invalid start date: {args.start_date}")

    if end_date < start_date:
        die("End date is before start date")

    results = {}
    roi = 0

    logging.debug("Querying Octopus Energy API")

    import_meter, export_meter = octopus_energy.get_tariff_history()

    octopus_energy_import_cost = octopus_energy.get_energy_cost_by_day(
        import_meter,
        start_date,
        end_date
    )

    octopus_energy_export_cost = octopus_energy.get_energy_cost_by_day(
        export_meter,
        start_date,
        end_date
    )

    logging.debug("Querying GivEnergy API")

    giv_energy_use = givenergy.get_energy_consumption_by_day(
        start_date,
        end_date
    )

    for date, result in giv_energy_use.items():
        results[date] = {}
        results[date]["grid_export"] = 0
        results[date]["grid_import"] = 0

        if date in octopus_energy_import_cost["consumption"]:
            # work out no PV cost
            no_pv_cost = 0.0
            for consumption_period in result["consumption_periods"]:
                # find price for this time
                for tariff_price in octopus_energy_import_cost["prices"][date]:
                    if tariff_price.is_active(consumption_period.valid_from):
                        no_pv_cost += tariff_price.price * consumption_period.consumption
                        break

            results[date] = {
                "home_consumption": result["total_home_consumption"],
                "no_pv_cost": round(no_pv_cost, 2),
                "cost": octopus_energy_import_cost["expenditure"][date],
                "grid_import": octopus_energy_import_cost["consumption"][date]
            }
        else:
            continue

        if date in octopus_energy_export_cost["generation"]:
            results[date]["income"] = octopus_energy_export_cost["income"][date]
            results[date]["grid_export"] = octopus_energy_export_cost["generation"][date]
        else:
            results[date]["income"] = 0
            results[date]["grid_export"] = 0
            results[date]["roi"] = 0

        results[date]["roi"] = (results[date]["no_pv_cost"] - results[date]["cost"]) + results[date]["income"]
        roi += results[date]["roi"]

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
                    logging.warning("%s: Missing fields: %s", date, ",".join(
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
