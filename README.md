# solar-roi

This project aims to calculate the Return On Investment (ROI) for a Solar panel system that uses a GivEnergy inverter and Octopus Energy as the supplier of electricity and as the buyer of exported electricity from the system.

It makes use of the GivEnergy and Octopus Energy APIs to correlate usage and the expenditure and income.

The `solar-roi.py` script that this project provides the ability to save historical records to a MySQL database. This then means that you can graph the records using Grafana for example.

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

You will need your GivEnergy API key and for Octopus Energy, you will require your API key, account number, electricity meter serial numbers and MPANs, and your electricity tariff and product codes.

If you want to save records to a MySQL database, then you will also need an operational MySQL server with a database and user for Solar-ROI to use.

## Execution

```bash
solar-roi.py -c path/to/solar-roi.conf --start 2023-08-01
```

The `--start` option specifies the date to process energy records from.

To save the records to MySQL, add the `--use-database` option to the command above.
