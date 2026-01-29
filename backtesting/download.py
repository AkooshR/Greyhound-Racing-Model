import betfairlightweight
import os
import time
import bz2
import json
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
from tqdm import tqdm

#Loads .env file into the environment. Assigns variables for each of the login details, and then logs into your betfair API.
load_dotenv()
KEY = str(os.getenv('BETFAIR_API_KEY'))
USERNAME = str(os.getenv('BETFAIR_USERNAME'))
PASSWORD = str(os.getenv('BETFAIR_PASSWORD'))
trading = betfairlightweight.APIClient(USERNAME, PASSWORD, KEY)
trading.login_interactive()

MAX_RETRIES = 6

#Getting all the available historic data in May 2020, and filtering for AvB markets (MATCH_BET). Outputs the file pathways for each AvB market!
#the for loop then checks if a file has already been downloaded. if not, it attempts to download it.

if input("Continue to download AvB files (type 'q'): ") == 'q':
    AvB_list = trading.historic.get_file_list(
    sport='Greyhound Racing',
    plan='Pro Plan',
    from_day='1',
    from_month='5',
    from_year='2020',
    to_day='31',
    to_month='5',
    to_year='2020',
    market_types_collection='MATCH_BET'
    )
    for file in AvB_list:
        for attempt in range(MAX_RETRIES):
            try:
                if not Path(f'backtestdata/{file.split('/')[8]}').exists():
                    trading.historic.download_file(file,"backtestdata")
                break  # Success, exit retry loop
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"Attempt {attempt + 1}/{MAX_RETRIES} failed for (AvB) {file}: {e}")
                else:
                    print(f"Failed to download {file} after {MAX_RETRIES} attempts")
                continue

time_curve = [0.5, 1, 2.5, 5.5, 9, 15]

JSON_PATH = 'backtesting/win_markets_may.json'
if input("Continue to generate win markets json file (type 'q'): ") == 'q':
    win_list = trading.historic.get_file_list(
        sport='Greyhound Racing',
        plan='Pro Plan',
        from_day='1',
        from_month='5',
        from_year='2020',
        to_day='31',
        to_month='5',
        to_year='2020',
        market_types_collection='WIN'
    )
    json_upload = {}
    for file in tqdm(win_list, desc="Processing WIN markets"):

        # this block attempts to download file
        for attempt in range(MAX_RETRIES):
            try:
                trading.historic.download_file(file,"winmarket")
                time.sleep(time_curve[attempt])
                
                # Verify the downloaded file is actually a valid bz2 file
                file_path = Path(f'winmarket/{file.split('/')[8]}')
                is_valid_bz2 = False
                with open(file_path, 'rb') as f:
                    magic = f.read(2)
                    is_valid_bz2 = (magic == b'BZ')
                
                if not is_valid_bz2:
                    # Not a valid bz2 file, probably HTML error page
                    time.sleep(0.5)  # Give time for file handle to release
                    os.remove(file_path)
                    raise ValueError(f"Downloaded file is not valid bz2 (got {magic}), likely HTML error page")
                
                break # Success, exit retry loop
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    print(f"\nAttempt {attempt + 1}/{MAX_RETRIES} failed for (WIN) {file}: {e}")
                else:
                    print(f"\nFailed to download {file} after {MAX_RETRIES} attempts")
                continue
        
        
        try:
            # continues if file failed to download
            if not Path(f'winmarket/{file.split('/')[8]}').exists():
                continue
            # the following code only runs if the file was successfully downloaded
            line1 = json.loads(next(bz2.open(Path(f'winmarket/{file.split('/')[8]}'), "rt")))
            date = line1['mc'][0]['marketDefinition']['marketTime'][:10]
            eventid = line1['mc'][0]['marketDefinition']['eventId']
            runner_list = []
            for runner in line1['mc'][0]['marketDefinition']['runners']:
                runner_list.append(runner['name'].split('.')[1].strip())
            race_length = line1['mc'][0]['marketDefinition']['name'].split()[1]
            os.remove(Path(f'winmarket/{file.split('/')[8]}'))
            json_upload.setdefault(eventid, []).append([date, race_length, runner_list])
            print(f"\nProcessed file: winmarket/{file.split('/')[8]}")
        except:
            print(f"\nError processing file: winmarket/{file.split('/')[8]}")
            continue

    try:
        json.dump(json_upload,open(JSON_PATH,'w'),indent=4)
    except:
        print("Error writing JSON file")
        print(json_upload)