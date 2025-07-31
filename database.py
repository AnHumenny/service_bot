import os
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

host = os.getenv('host')
port = os.getenv('port')
user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')

DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}/{database}"  # маршрут в основной проект

engine = create_async_engine(url=DATABASE_URL)
new_session = async_sessionmaker(engine, expire_on_commit=False)


class Model(DeclarativeBase):
    id = Column(Integer, primary_key=True, autoincrement=True)


class DAccident(Model):                                 # большую часть классов можно взять с service
    __tablename__ = "accident_accident"
    number = Column(String(10))
    category = Column(String(20))
    sla = Column(String(20))
    datetime_open = Column(DateTime, default=datetime.utcnow)
    datetime_close = Column(DateTime, default=datetime.utcnow)
    problem = Column(String(2000))
    city = Column(String(255))
    address = Column(String(500))
    name = Column(String(100))
    phone = Column(String(13))
    subscriber = Column(String(13))
    comment = Column(String(2000))
    decide = Column(String(2000))
    status = Column(String(5))


class DGazprom(Model):
    __tablename__ = "gazprom_gazprom"
    ip = Column(String(15))
    number = Column(String(10))
    address = Column(String(255))
    type = Column(String(10))
    region = Column(String(100))
    comment = Column(String(500))
    geo = Column(String(30))


class DManual(Model):
    __tablename__ = "manual_manual"
    model = Column(String(255))
    description = Column(Text)


class DUser(Model):
    __tablename__ = "_userbot"
    login = Column(String(30))
    name = Column(String(30))
    status = Column(String(15))
    password = Column(String)
    phone = Column(String(14))
    email = Column(String(50))
    tg_id = Column(String(50))


class DVisitedUser(Model):
    __tablename__ = "_visited_users"
    login = Column(String(30))
    date_created = Column(DateTime(timezone=False))
    action = Column(String(50))


class DBaseStation(Model):
    __tablename__ = "base_station_basestation"
    comment = Column(String(255))
    address = Column(String(255))
    number = Column(Integer())


class DAllInfo(Model):
    __tablename__ = "fttx_fttx"
    city = Column(String(20))
    claster = Column(String(20))
    street = Column(String(30))
    number = Column(String(10))
    description = Column(Text(1000))
    askue = Column(Integer)


class DAddInfo(Model):
    __tablename__ = "info_info"
    reestr = Column(Integer)
    date_created = Column(DateTime(timezone=False))
    city = Column(String(20))
    street = Column(String(30))
    home = Column(String(7))
    apartment = Column(String(4))
    name = Column(String(100))
    cable_1 = Column(Integer)
    cable_2 = Column(Integer)
    cable_3 = Column(Integer)
    connector = Column(Integer)
