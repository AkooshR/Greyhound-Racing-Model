import bz2
import json
import pandas as pd
from pathlib import Path
import main as main

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

    date = ""
    commission = 0.0

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
            for runner in json.loads(line)['mc'][0]['marketDefinition']['runners']:
                runner_id = runner['id']
                runner_name = runner['name'].split('.')[1].strip()
                runner_status = runner['status']
                runner_details[runner_name] = [runner_id,runner_status]

        line_number += 1
                
    return runner_details, runner_odds_dict, date, commission

for filepath in Path("backtestdata").iterdir():
    print(filepath)
    number_of_lines = count_lines(filepath)
    runner_details, runner_odds_dict, date, commission = read_file(filepath,number_of_lines)
    runner_names = []
    for runner in runner_details.keys():
        runner_names.append(runner)
        odds_list = runner_odds_dict[runner_details[runner][0]]
        mean_back = sum(odds_list) / len(odds_list)
        print(f"file: {filepath.name}, \
              \n\tdate: {date} \
              \n\trunner: {runner} \
              \n\tstatus: {runner_details[runner][1]} \
              \n\tmean available-to-back odds: {mean_back:.2f} \
              \n\tcommission: {commission:.2f} \n")
        
        
