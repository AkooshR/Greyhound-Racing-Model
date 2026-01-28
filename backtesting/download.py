import betfairlightweight
import os
import bz2
import json
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path

#Loads .env file into the environment. Assigns variables for each of the login details, and then logs into your betfair API.
load_dotenv()
KEY = str(os.getenv('BETFAIR_API_KEY'))
USERNAME = str(os.getenv('BETFAIR_USERNAME'))
PASSWORD = str(os.getenv('BETFAIR_PASSWORD'))
trading = betfairlightweight.APIClient(USERNAME, PASSWORD, KEY)
trading.login_interactive()

#Getting all the available historic data in May 2020, and filtering for AvB markets (MATCH_BET). Outputs the file pathways for each AvB market!
#the for loop then checks if a file has already been downloaded. if not, it attempts to download it.
#AvB_list = trading.historic.get_file_list(
#    sport='Greyhound Racing',
#    plan='Pro Plan',
#    from_day='1',
#    from_month='5',
#    from_year='2020',
#    to_day='31',
#    to_month='5',
#    to_year='2020',
#    event_id=None,
#    event_name=None,
#    market_types_collection='MATCH_BET'
#)
#for file in AvB_list:
#    if not Path(f'backtestdata/{file.split('/')[8]}').exists():
#        trading.historic.download_file(file,"backtestdata")