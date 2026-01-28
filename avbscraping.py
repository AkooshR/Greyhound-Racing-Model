import betfairlightweight
import os
import pandas as pd
from dotenv import load_dotenv
from pathlib import Path
import os
from zoneinfo import ZoneInfo
import main as main
import time

#Loads .env file into the environment. Assigns variables for each of the login details, and then logs into your betfair API.
load_dotenv()
KEY = os.getenv('BETFAIR_API_KEY')
USERNAME = os.getenv('BETFAIR_USERNAME')
PASSWORD = os.getenv('BETFAIR_PASSWORD')
trading = betfairlightweight.APIClient(USERNAME, PASSWORD, KEY)
trading.login_interactive()

# Find the event type ID for Greyhound Racing
event_types = trading.betting.list_event_types(filter=filters.market_filter())
greyhound_event_type_id = None
for et in event_types:
    if et.event_type.name == "Greyhound Racing":
        print("Greyhound Racing market found!")
        greyhound_event_type_id = et.event_type.id
        break

if not greyhound_event_type_id:
    trading.logout()
    raise SystemExit("Greyhound Racing event type not found.")

# Get upcoming AvB markets
# Return all races today
def get_next_races(market_type):
    now_local = datetime.datetime.now(MELB)
    midnight_local = now_local.replace(hour=23, minute=59, second=59)
    now_utc = now_local.astimezone(UTC)
    midnight_utc = midnight_local.astimezone(UTC)

    market_catalogue = trading.betting.list_market_catalogue(
        filter=filters.market_filter(
            event_type_ids=[greyhound_event_type_id],
            #country_codes=["AU"],
            market_type_codes=[market_type],
            market_start_time={"from": iso_z(now_utc), "to": iso_z(midnight_utc)},
        ),
        market_projection=["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"],
        max_results=1000, 
    )

    if not market_catalogue:
        print("Tried to find requested AvB markets but failed.")

    return market_catalogue


def get_runner_names(market_id, runner_name, market_name):
    # Only process MATCH_BET markets
    if " v " not in market_name:
        return []
    
    books = trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection=filters.price_projection(price_data=["EX_BEST_OFFERS"]),
        )

    runner_names = []
    if not books:
        print("No market book returned. Is the market requested available?")
        return []
    
    for r in books[0].runners:
        name = runner_name.get(r.selection_id, str(r.selection_id))
        runner_names.append(name)

    return runner_names

def get_distance(race, win_catalogue):
    event_name = race.event.name if race.event else "Unknown Event"
    event_start = to_melbourne(race.market_start_time) 

    for win_race in win_catalogue:
        if win_race.event.name == event_name \
          and to_melbourne(win_race.market_start_time) == event_start:
            return str(win_race.market_name).split()[1]
    
    print(f"Distance for requested race not found!")
    return ""

market_catalogue = get_next_races("MATCH_BET")
win_catalogue = get_next_races("WIN")
for race in market_catalogue:
    market_id = race.market_id
    event_name = race.event.name if race.event else "Unknown Event"
    start_local = to_melbourne(race.market_start_time)

    # Map selectionId to runner name
    runner_name = {r.selection_id: r.runner_name for r in (race.runners or [])}
    race_length = int(get_distance(race, win_catalogue)[0:-1])
    race_date = start_local.strftime('%Y-%m-%d')

    print(f"\n\n\n\n========================")

    print(f"\nFound a market! Tracking...")
    print(f"\tMarket ID:  {market_id}")
    print(f"\tEvent:      {event_name}")
    print(f"\tStart:      {start_local.strftime('%Y-%m-%d %H:%M:%S %Z')} (Melbourne)")
    print(f"\tDistance:   {race_length}m")

    runner_names = get_runner_names(market_id, runner_name, race.market_name)
    formatted_names = []

    for name in runner_names:
        print(f"{name:22s}")
        formatted_names.append(name.split('.')[1].strip())

    runner1_name = formatted_names[0]
    runner2_name = formatted_names[1]

    table1 = main.read_greyhound_data(runner1_name, race_length, race_date)
    table2 = main.read_greyhound_data(runner2_name, race_length, race_date)

    if table1.shape[0] in (0, 1) or table2.shape[0] in (0, 1):
        print("ERROR: Unable to retrieve data for one or both greyhounds.")
    else:
        runner1_params = main.fit_normal_dist(table1)
        runner2_params = main.fit_normal_dist(table2)

        prob_runner1, prob_runner2 = main.simulate(runner1_params, runner2_params)
        fair_odds1 = 1 / prob_runner1 if prob_runner1 != 0 else None
        fair_odds2 = 1 / prob_runner2 if prob_runner2 != 0 else None

        print(f"\n-----RESULTS-----")

        print(f"{runner1_name}:")
        print(f"\tFair odds    : {fair_odds1:.2f}")
        print(f"\tWin %        : {100*prob_runner1:.2f}")
        print(f"\tNo. samples  : {len(table1)}")
        print(f"\tMean time    : {table1['Time'].mean():.2f} ")

        print(f"{runner2_name}:")
        print(f"\tFair odds    : {fair_odds2:.2f}")
        print(f"\tWin %        : {100*prob_runner2:.2f}")
        print(f"\tNo. samples  : {len(table2)}")
        print(f"\tMean time    : {table2['Time'].mean():.2f} ")

    time.sleep(1)

print("All done! Logging out...")
trading.logout()
exit(0)
