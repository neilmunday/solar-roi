import configparser
import logging
import pathlib
import sys

import solarroi


def check_file(f: pathlib.Path):
    """
    Check if the given file exists, exit if it does not.
    """
    if not f.is_file():
        die(f"{f} does not exist")


def die(msg: str):
    """
    Exit the program with the given error message.
    """
    logging.error(msg)
    sys.exit(1)


def get_config_opion(section_name: str, option_name: str) -> str:
    check_file(solarroi.conf_file)
    parser = configparser.ConfigParser()
    parser.read(solarroi.conf_file)

    if not parser.has_section(section_name):
        die(f"Could not find section {section_name} in {solarroi.conf_file}")

    if not parser.has_option(section_name, option_name):
        die(f"Section {section_name} has no option {option_name}")

    return parser.get(section_name, option_name)
