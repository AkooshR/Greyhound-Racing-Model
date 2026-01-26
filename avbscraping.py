import betfairlightweight
from betfairlightweight import filters
import datetime
import json
import time
from dotenv import load_dotenv
from pathlib import Path
import os
from zoneinfo import ZoneInfo

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BETFAIR_PASSWORD = os.getenv("BETFAIR_PASSWORD")
BETFAIR_API_KEY = os.getenv("BETFAIR_API_KEY")

print(BETFAIR_PASSWORD)

