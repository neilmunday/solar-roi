import logging

from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy import create_engine, Column, Date, DateTime, Double  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore

from solarroi.common import get_config_opion

CONFIG_SECTION = "MySQL"

Base = declarative_base()


def connect_db() -> sessionmaker:
    db = get_config_opion(CONFIG_SECTION, "database")
    user = get_config_opion(CONFIG_SECTION, "user")
    password = get_config_opion(CONFIG_SECTION, "password")
    host = get_config_opion(CONFIG_SECTION, "host")

    conn_str = f"mysql+pymysql://{user}:{password}@{host}/{db}"
    logging.debug("connect_db: connecting to: %s", conn_str)
    engine = create_engine(conn_str)
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    return Session


class SolarROI(Base):  # type: ignore

    __tablename__ = "roi"

    date = Column(Date, primary_key=True)
    cost = Column(Double)
    grid_export = Column(Double)
    grid_import = Column(Double)
    home_consumption = Column(Double)
    income = Column(Double)
    no_pv_cost = Column(Double)
    roi = Column(Double)


class Solcast(Base):  # type: ignore

    __tablename__ = "solcast"

    date = Column(DateTime, primary_key=True)
    pv_estimate = Column(Double)
