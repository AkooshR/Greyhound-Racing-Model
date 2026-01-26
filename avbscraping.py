import betfairlightweight
from betfairlightweight import filters
import datetime
from dotenv import load_dotenv
from pathlib import Path
import os
import json
import time
from zoneinfo import ZoneInfo

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

BETFAIR_USERNAME = str(os.getenv("BETFAIR_USERNAME"))
BETFAIR_PASSWORD = str(os.getenv("BETFAIR_PASSWORD"))
BETFAIR_API_KEY = str(os.getenv("BETFAIR_API_KEY"))

# Set timezone to Melbourne, Australia
MELB = ZoneInfo("Australia/Melbourne")
UTC = datetime.timezone.utc

def iso_z(dt_aware_utc: datetime.datetime) -> str:
    return dt_aware_utc.strftime("%Y-%m-%dT%H:%M:%S.000Z")

def to_melbourne(dt) -> datetime.datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(MELB)

# Access Betfair API
trading = betfairlightweight.APIClient(
    username=BETFAIR_USERNAME,
    password=BETFAIR_PASSWORD,
    app_key=BETFAIR_API_KEY
)
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
# Only search for races up to 1 hour from now
now_local = datetime.datetime.now(MELB)
later_local = now_local + datetime.timedelta(hours=1)
now_utc = now_local.astimezone(UTC)
later_utc = later_local.astimezone(UTC)

market_catalogue = trading.betting.list_market_catalogue(
    filter=filters.market_filter(
        event_type_ids=[greyhound_event_type_id],
        market_type_codes=["WIN"],
        market_start_time={"from": iso_z(now_utc), "to": iso_z(later_utc)},
    ),
    market_projection=["RUNNER_DESCRIPTION", "EVENT", "MARKET_START_TIME"],
    max_results=5, 
)

if not market_catalogue:
    trading.logout()
    raise SystemExit("No upcoming greyhound AvB markets found in the time window.")

first_market = market_catalogue[0]
market_id = first_market.market_id
event_name = first_market.event.name if first_market.event else "Unknown Event"
start_local = to_melbourne(first_market.market_start_time)

# Map selectionId to runner name
runner_name = {r.selection_id: r.runner_name for r in (first_market.runners or [])}

print(f"\nFound a market! Tracking...")
print(f"\tMarket ID: {market_id}")
print(f"\tEvent:     {event_name}")
print(f"\tStart:     {start_local.strftime('%Y-%m-%d %H:%M:%S %Z')} (Melbourne)\n")


# map runner to prices (avg of back and lay) every second
prices = {}

def overround(book: list) -> float:
    overround = 0.0
    for price in book:
        overround += 1.0 / price
    return overround

# poll market
POLL_SECONDS = 1.0

try:
    while True:
        books = trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection=filters.price_projection(price_data=["EX_BEST_OFFERS"]),
        )

        if not books:
            print("No market book returned. Is the market requested available?")
            time.sleep(POLL_SECONDS)
            continue

        book = books[0]
        tstamp = datetime.datetime.now(MELB).strftime("%Y-%m-%d %H:%M:%S %Z")
        time_to_jump = start_local - datetime.datetime.now(MELB)

        print(f"\n{str(time_to_jump).split('.')[0]} to jump | {book.status} (In play: {book.inplay})")

        # If the market is closed, you can break
        if book.status in ("CLOSED", "SETTLED"):
            print("Market closed/settled. Stopping.")
            break

        # Print best back/lay for each runner
        lay_book = []
        lpm = {}
        for r in book.runners:
            name = runner_name.get(r.selection_id, str(r.selection_id))

            atb = r.ex.available_to_back
            atl = r.ex.available_to_lay
            lpm[name] = r.get("lastPriceTraded") if r.get("lastPriceTraded") else None

            best_back = atb[0].price if atb else None
            best_lay = atl[0].price if atl else None

            print(f"{name:22s}  Back={best_back!s:>6}  Lay={best_lay!s:>6}  LPM={lpm[name]!s:>6}")
            lay_book.append(best_lay if best_lay else float('inf'))

        ornd = overround(lay_book)
        print(f"Lay efficiency: {ornd:.4f}")
        if ornd < 0.88:
            print("WARNING: Prices may be unreliable.")
        
        # store last price matched
        if lpm:
            for name in lpm:
                if name not in prices:
                    prices[name] = []
                if lpm[name] is not None:
                    prices[name].append(lpm[name])

        time.sleep(POLL_SECONDS)

except KeyboardInterrupt:
    print("\nStopped by user (Ctrl+C).")
    print("Final prices collected:")
    for runner, price_list in prices.items():
        print(f"{runner:22s}  Prices: {', '.join(f'{p:.2f}' for p in price_list)}")
        

finally:
    trading.logout()
    print("Logged out.")
    print("Final prices collected:")
    for runner, price_list in prices.items():
        print(f"{runner:22s}  Prices: {', '.join(f'{p:.2f}' for p in price_list)}")