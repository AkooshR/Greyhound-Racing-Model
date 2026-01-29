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
AvB_list = trading.historic.get_file_list(
    sport='Greyhound Racing',
    plan='Pro Plan',
    from_day='1',
    from_month='5',
    from_year='2020',
    to_day='31',
    to_month='5',
    to_year='2020',
    event_id=None,
    event_name=None,
    market_types_collection='MATCH_BET'
)

if input("Continue to download files (type 'q'): ") == 'q':
    for file in AvB_list:
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES):
            try:
                if not Path(f'backtestdata/{file.split('/')[8]}').exists():
                    trading.historic.download_file(file,"backtestdata")
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for {file}: {e}")
                else:
                    print(f"Failed to download {file} after {MAX_RETRIES} attempts")
                continue

win_list = trading.historic.get_file_list(
    sport='Greyhound Racing',
    plan='Pro Plan',
    from_day='1',
    from_month='5',
    from_year='2020',
    to_day='31',
    to_month='5',
    to_year='2020',
    event_id=None,
    event_name=None,
    market_types_collection='WIN'
)
json_upload = {}
json_file = open('win_markets_may.json','w')
for file in win_list:
    trading.historic.download_file(file,"winmarket")
    line1 = json.loads(next(bz2.open(Path(f'winmarket/{file.split('/')[8]}'), "rt")))
    date = line1['mc'][0]['marketDefinition']['marketTime'][:10]
    eventid = line1['mc'][0]['marketDefinition']['eventId']
    runner_list = []
    for runner in line1['mc'][0]['marketDefinition']['runners']:
        runner_list.append(runner['name'].split('.')[1].strip())
    race_length = line1['mc'][0]['marketDefinition']['name'].split()[1]
    json_upload.setdefault(eventid, []).append([date, race_length, runner_list])
    print(json_upload)
    os.remove(Path(f'winmarket/{file.split('/')[8]}'))

json.dump(json_upload,json_file,indent=4)