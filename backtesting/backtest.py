import bz2
import json
import pandas as pd
from pathlib import Path

# count the number of lines in this file
def count_lines(filepath):
    number_of_lines = 0
    for line in bz2.open(filepath,"rt"):
        number_of_lines += 1
    return number_of_lines

MIN_VOLUME = 5
def process_line(line, runner_odds_dict):
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
LINES_PROCESSED = 50
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
            commission = json.loads(line)['mc'][0]['marketDefinition']['marketBaseRate']
            date = json.loads(line)['mc'][0]['marketDefinition']['marketTime'][:10]
            eventid = json.loads(line)['mc'][0]['marketDefinition']['eventId']
            for runner in json.loads(line)['mc'][0]['marketDefinition']['runners']:
                runner_id = runner['id']
                runner_name = runner['name'].split('.')[1].strip()
                runner_status = runner['status']
                runner_details[runner_name] = [runner_id,runner_status]

        line_number += 1
                
    return runner_details, runner_odds_dict, date, commission,eventid

JSON_PATH = 'backtesting/win_markets_may.json'
for filepath in Path("backtestdata").iterdir():
    number_of_lines = count_lines(filepath)
    runner_details, runner_odds_dict, date, commission, eventid = read_file(filepath,number_of_lines)
    for runner in runner_details.keys():
        odds_list = runner_odds_dict[runner_details[runner][0]]
        mean_back = sum(odds_list) / len(odds_list)
        print(f"file: {filepath.name}, \
              \n\tdate: {date} \
              \n\trunner: {runner} \
              \n\tstatus: {runner_details[runner][1]} \
              \n\tmean available-to-back odds: {mean_back:.2f} \
              \n\tcommission: {commission:.2f} \n")
    json_file = json.load(open(JSON_PATH,'r'))
    for race in json_file[eventid]:
        date_matches = race[0] == date
        runners_match = list(runner_details.keys())[0] in race[2] and list(runner_details.keys())[1] in race[2]
        if date_matches and runners_match:
            distance = int(race[1][:-1])
            print(f'race found, distance is {distance}')
            break