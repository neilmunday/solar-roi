# solar-roi

This project aims to calculate the Return On Investment (ROI) for a Solar panel system that uses a GivEnergy inverter and Octopus Energy as the supplier of electricity and as the buyer of exported electricity from the system.

It makes use of the GivEnergy and Octopus Energy APIs to correlate usage and the expenditure and income.

The `solar-roi.py` script provided by this project has the ability to save historical records to a MySQL database. This then means that you can graph the records using Grafana for example.

In addition the `solar-forecast.py` script is provided to download solar forecast data for your location using the [Solcast API](https://solcast.com/) when using a "hobbyist" account.

## Requirements

* requests
* PyMySQL
* SQLAlchemy

## Installation

### SetupTools

```bash
python3 setup.py install
```

### Manual

Download the latest release of this project or use `git clone https://github.com/neilmunday/solar-roi` command to download the latest code to a directory of your choice.

## Configuration

Solar-ROI requires a configuration file, `solar-roi.conf`. An example is provided in the `etc` directory of this project.

You will need your GivEnergy API key and for Octopus Energy, you will require your API key and account number.

If you want to save records to a MySQL database, then you will also need an operational MySQL server with a database and user for Solar-ROI to use.

If you also want to download solar forecast data you will need to add your Solcast API key and resource ID to `solar-roi.conf`.

## Execution

### solar-roi.py

Using a specific start date:

```bash
solar-roi.py -c path/to/solar-roi.conf --start 2023-08-01
```

Use a date range:

```bash
solar-roi.py -c path/to/solar-roi.conf --start 2023-08-01 --end 2023-09-01
```

Using a relative start date (today minus 3 days):

```bash
solar-roi.py -c path/to/solar-roi.conf --start now-3
```

The `--start` option specifies the date to process energy records from. You can use a specific date or a relative date by specifying the string `now-X` where `X` is the number of days to substract from the current date.

To save the records to MySQL, add the `-d` or `--use-database` option to the command above.

### solar-forecast.py

Download the forecast for your location and save to MySQL:

```bash
solar-forecast.py -c path/to/solar-roi.conf --d
```
