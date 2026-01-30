import bz2
import csv
import json
import pandas as pd
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
import main as main
from hypothesistesting import betting_p_value

# count the number of lines in this file
def count_lines(filepath):
    number_of_lines = 0
    for line in bz2.open(filepath,"rt"):
        number_of_lines += 1
    return number_of_lines


# --- RESUME SKIP START --- (if you accidently stop the backtest halfway through, resume on a specific runner)
#RESUME_SKIP_UNTIL_RUNNER = "Scott Hooked"
#resume_reached = False
# --- RESUME SKIP END ---
MIN_VOLUME = 5
def process_line(line, runner_odds_dict):
    """
    Get the 'reasonable back odds' for each runner by getting either traded odds or available-to-back odds.

    Last price matched (traded odds) is preferred, and either is only recorded if the volume is above `MIN_VOLUME`.
    """
    formatted_line = json.loads(line)['mc'][0]['rc']
    for runner_changes in formatted_line:
        runner_id = runner_changes['id']
        if 'trd' in runner_changes:
            if runner_changes['trd'][0][1] > MIN_VOLUME:
                runner_odds_dict.setdefault(runner_id, []).append(runner_changes['trd'][0][0])
        elif 'atb' in runner_changes:
            if runner_changes['atb'][0][1] > MIN_VOLUME:
                runner_odds_dict.setdefault(runner_id, []).append(runner_changes['atb'][0][0])

# go through the last 50 lines, and collect all the available-to-back odds for each runner
LINES_PROCESSED = 18
def read_file(filepath,number_of_lines):
    runner_details = {}
    runner_odds_dict = {}

    file_handle = bz2.open(filepath, "rt")
    line_number = 0
    date = ""
    commission = 0.0
    eventid = ""

    # skip through until we reach the last `LINES_PROCESSED` lines
    while line_number < number_of_lines - LINES_PROCESSED:
        next(file_handle)
        line_number += 1

    # read all odds data in each line and store them
    for line in file_handle:
        # process all lines except the last line
        if line_number != number_of_lines - 1:
            process_line(line, runner_odds_dict)
				
        # map runner name to runner_details
        else:
            md = json.loads(line)['mc'][0]['marketDefinition']
            commission = md['marketBaseRate']
            date = md['marketTime'][:10]
            eventid = md['eventId']
            for runner in md['runners']:
                runner_id = runner['id']
                runner_name = runner['name'].split('.')[1].strip()
                runner_status = runner['status']
                runner_details[runner_name] = [runner_id,runner_status]

        line_number += 1
    
    # variables needed for backtest and race matching to find distance
    return runner_details, runner_odds_dict, date, commission, eventid

def get_distance_from_json(eventid, date, runner_details, win_market_data):
    """
    Finds the distance of a race by matching eventid, date, and runner names to the win market data stored in JSON.
    """
    distance = 0
    for race in win_market_data.get(eventid, []):
        date_matches = race[0] == date
        runners_match = list(runner_details.keys())[0] in race[2] and list(runner_details.keys())[1] in race[2]
        fdistance = race[1][:-1] # gets the distance, removes the 'm' at the end
        if date_matches and runners_match and fdistance.isdigit():
            distance = int(fdistance)
    return distance

def calculate_overround(runner1_odds, runner2_odds):
    """
    Calculates the overround for a two-runner market.

    Defined as the sum of implied probabilities i.e. 1 / runner1_odds + 1 / runner2_odds.
    """
    if runner1_odds is None or runner2_odds is None:
        return 1.0
    overround = (1.0 / runner1_odds) + (1.0 / runner2_odds)
    return overround

JSON_PATH = 'backtesting/win_markets_may.json'
win_market_data = json.load(open(JSON_PATH, 'r'))

offered_odds = []
results = []
commissions = []
overrounds = []
files_processed = 0
files_skipped = 0
bets_placed = 0
wins = 0

results_path = Path("backtestresult.csv")
write_header = not results_path.exists()
results_file = results_path.open("a", newline="")
results_writer = csv.writer(results_file)
if write_header:
    results_writer.writerow(["fair_odds", "given_odds", "commission", "outcome", "overround"])

for filepath in Path("backtestdata").iterdir():
    if filepath.suffix not in ('.bz2', '.bz'):
        continue
    files_processed += 1

     # extract runner and market details from file
    runner_names = []
    number_of_lines = count_lines(filepath)
    runner_details, runner_odds_dict, date, commission, eventid = read_file(filepath, number_of_lines)
    # --- RESUME SKIP START ---
    #if not resume_reached:
    #    if RESUME_SKIP_UNTIL_RUNNER in runner_details:
    #        resume_reached = True
    #        continue
    #    continue
    # --- RESUME SKIP END ---
    commission_rate = commission / 100 if commission >= 1 else commission
    
    # extract distance by matching date and runners to win market
    distance = get_distance_from_json(eventid, date, runner_details, win_market_data)
    if distance == 0:
        files_skipped += 1
        continue

    # get runner names and back odds
    for runner_name in runner_details.keys():
        runner_id = runner_details[runner_name][0]
        back_odds_list = runner_odds_dict[runner_id] if runner_id in runner_odds_dict else [] 
        if not back_odds_list:
            runner_details[runner_name].append(None)
        else:
            mean_back = sum(back_odds_list) / len(back_odds_list)
            runner_details[runner_name].append(mean_back)

        runner_names.append(runner_name)

    # valid data is True if both runners have at least MIN_RACES samples
    (fair_odds1, fair_odds2), valid_data = main.runner_analysis(runner_names[0], runner_names[1], distance, date)

    if not valid_data:
        files_skipped += 1
        continue

    # offered odds
    offered1 = runner_details[runner_names[0]][2]
    offered2 = runner_details[runner_names[1]][2]
    print(
        f"Back odds: {runner_names[0]}={offered1}, {runner_names[1]}={offered2}"
    )
    overround = calculate_overround(offered1, offered2)

    if offered1 is None or offered2 is None or fair_odds1 is None or fair_odds2 is None:
        files_skipped += 1
        continue

    ev1 = main.calculate_ev(fair_odds1, offered1, commission_rate)
    ev2 = main.calculate_ev(fair_odds2, offered2, commission_rate)

    if ev1 <= 0.10 and ev2 <= 0.10:
        files_skipped += 1
        continue

    # hypothetical bet, choose the favoured runner
    if ev1 >= ev2:
        chosen_name = runner_names[0]
        chosen_odds = offered1
        chosen_fair_odds = fair_odds1
    else:
        chosen_name = runner_names[1]
        chosen_odds = offered2
        chosen_fair_odds = fair_odds2

    # resolve bet
    chosen_status = runner_details[chosen_name][1]
    if chosen_status not in ("WINNER", "LOSER"):
        files_skipped += 1
        continue

    bet_result = "W" if chosen_status == "WINNER" else "L"
    offered_odds.append(chosen_odds)
    results.append(bet_result)
    commissions.append(commission_rate)
    overrounds.append(overround)

    # write to `backtestresult.csv`
    # used for hypothesis testing later
    results_writer.writerow([chosen_fair_odds, chosen_odds, commission_rate, bet_result, overround])
    results_file.flush() # allows data to be written immediately
    print("Added bet to results:", chosen_name, chosen_fair_odds, chosen_odds, commission, bet_result, overround)
    bets_placed += 1
    if bet_result == "W":
        wins += 1

results_file.close()

if offered_odds:
    avg_commission = sum(commissions) / len(commissions)
    p_value = betting_p_value(offered_odds, results, commissions)
    print("\n-----BACKTEST SUMMARY-----")
    print(f"Files processed: {files_processed}")
    print(f"Files skipped  : {files_skipped}")
    print(f"Bets placed    : {bets_placed}")
    print(f"Wins           : {wins}")
    print(f"Win rate       : {wins / bets_placed:.2%}")
    print(f"Avg commission : {avg_commission:.4f}")
    print(f"Avg overround  : {sum(overrounds) / len(overrounds):.2f}%")
    print(f"P-value        : {p_value:.4f}")
else:
    print("\nNo qualifying bets were placed. P-value not computed.")