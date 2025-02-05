import os
from sqlalchemy import create_engine
import pymysql
from servers.server_settings import market_profile_db
pymysql.install_as_MySQLdb()

SQLALCHEMY_DATABASE_URI = "mysql+mysqldb://admin:niftybull0803@fin-db.ccmbzbemnwg9.us-east-1.rds.amazonaws.com/market_data"
SQLALCHEMY_SQLITE_DATABASE_URI = "sqlite:///" + os.path.abspath(market_profile_db)  # works


def get_db_sqlite_engine():
    engine = create_engine(SQLALCHEMY_SQLITE_DATABASE_URI)
    return engine

def get_db_engine():
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    return engine
