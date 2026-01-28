import betfairlightweight
from betfairlightweight import filters
import datetime
from dotenv import load_dotenv
from pathlib import Path
import os
from zoneinfo import ZoneInfo
import main as main
import time

# BETFAIR ACCOUNT DETAILS
#
# Create a file '.env' and copy the template below:
# BETFAIR_USERNAME = 
# BETFAIR_PASSWORD = 
# BETFAIR_API_KEY = 

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BETFAIR_USERNAME = str(os.getenv("BETFAIR_USERNAME"))
BETFAIR_PASSWORD = str(os.getenv("BETFAIR_PASSWORD"))
BETFAIR_API_KEY = str(os.getenv("BETFAIR_API_KEY"))

# Access Betfair API
trading = betfairlightweight.APIClient(
    username=BETFAIR_USERNAME,
    password=BETFAIR_PASSWORD,
    app_key=BETFAIR_API_KEY
)
trading.login_interactive()

# Helper functions for moving between Melbourne time and UTC time
MELB = ZoneInfo("Australia/Melbourne")
UTC = datetime.timezone.utc

def iso_z(dt_aware_utc: datetime.datetime) -> str:
    """
    Formats a UTC datetime object into a formatted string (ISO 8601).
    """
    return dt_aware_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def to_melbourne(dt) -> datetime.datetime:
    """
    Converts timezone-aware datetime objects into Melbourne time.

    Assumes UTC if input is timezone-naive.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MELB)



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
    """
    Searches for races of the requested `market_type` from now until midnight same day.

    :param str market_type: e.g. "WIN" or "MATCH_BET" (AvB)

    :returns out: dict
    """
    # Search until midnight same day
    now_local = datetime.datetime.now(MELB)
    midnight_local = now_local.replace(hour=23, minute=59, second=59)
    now_utc = now_local.astimezone(UTC)
    midnight_utc = midnight_local.astimezone(UTC)

    # Returns a dict of all requested `market_type` markets
    market_catalogue = trading.betting.list_market_catalogue(
        filter=filters.market_filter(
            event_type_ids=[greyhound_event_type_id],
            market_type_codes=[market_type],
            market_start_time={"from": iso_z(now_utc), "to": iso_z(midnight_utc)},
        ),
        market_projection=["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"],
        max_results=1000, 
    )

    if not market_catalogue:
        print("Tried to find requested AvB markets but failed.")

    return market_catalogue


def get_runner_names(market_id, runner_name):
    """
    Returns a list of runner names in `market_id`.

    :param str market_id: market id of the AvB market
    :param dict runner_name: a map of runner selection ids to their names as a string
    """
    
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
    """
    Finds the same race in the `WIN` market by matching, then returns the distance (e.g. "300m")
    """
    event_name = race.event.name if race.event else "Unknown Event"
    event_start = to_melbourne(race.market_start_time) 

    for win_race in win_catalogue:
        if win_race.event.name == event_name \
          and to_melbourne(win_race.market_start_time) == event_start:
            return str(win_race.market_name).split()[1]
    
    print(f"Distance for requested race not found!")
    return ""

market_catalogue = get_next_races("MATCH_BET")
win_catalogue = get_next_races("WIN") # only needed to find distances of races

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

    runner_names = get_runner_names(market_id, runner_name)
    formatted_names = []

    for name in runner_names:
        print(f"{name:22s}")
        formatted_names.append(name.split('.')[1].strip())

    runner1_name = formatted_names[0]
    runner2_name = formatted_names[1]

    main.print_runner_analysis(runner1_name, runner2_name, race_length, race_date)

    time.sleep(1)

print("All done! Logging out...")
trading.logout()
exit(0)