#!/usr/bin/env python3

import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))

import solarroi.cli  # noqa

if __name__ == "__main__":
    solarroi.cli.solar_forecast_main()
