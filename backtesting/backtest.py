import bz2
import json
import pandas as pd
from pathlib import Path

#count the number of lines in this file
def count_lines(filepath):
    number_of_lines = 0
    for line in bz2.open(filepath,"rt"):
        number_of_lines += 1
    return number_of_lines

#go through the last 50 lines, and collect all the available-to-back odds for each runner
def read_file(filepath,number_of_lines):
    runner_names = {}
    runner_odds_dict = {}
    line_number = 0
    for line in bz2.open(filepath,"rt"):
        line_number += 1
        if line_number >= number_of_lines-49 and line_number != number_of_lines:
            formatted_line = json.loads(line)['mc'][0]['rc']
            for runner_changes in formatted_line:
                runner_id = runner_changes['id']
                if 'trd' in runner_changes:
                    if runner_id not in runner_odds_dict:
                        runner_odds_dict[runner_id] = []
                    if runner_changes['trd'][0][1] > 5:
                        runner_odds_dict[runner_id].append(runner_changes['trd'][0][0])
                elif 'atb' in runner_changes:
                    if runner_id not in runner_odds_dict:
                        runner_odds_dict[runner_id] = []
                    if runner_changes['atb'][0][1] > 5:
                        runner_odds_dict[runner_id].append(runner_changes['atb'][0][0])
        elif line_number == number_of_lines:
            for i in range(2):
                runner_id = json.loads(line)['mc'][0]['marketDefinition']['runners'][i]['id']
                runner_name = json.loads(line)['mc'][0]['marketDefinition']['runners'][i]['name'].split('.')[1].strip()
                runner_status = json.loads(line)['mc'][0]['marketDefinition']['runners'][i]['status']
                runner_names[runner_name] = [runner_id,runner_status]
        elif line_number == 1:
            print(json.loads(line)['mc'][0]['marketDefinition'])
    return runner_names, runner_odds_dict

for filepath in Path("backtestdata").iterdir():
    number_of_lines = count_lines(filepath)
    runner_names, runner_odds_dict = read_file(filepath,number_of_lines)
    print(runner_names)
    print(runner_odds_dict)
    for runner in runner_names.keys():
        odds_list = runner_odds_dict[runner_names[runner][0]]
        mean_back = sum(odds_list)/len(odds_list)