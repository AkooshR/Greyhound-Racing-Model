import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def read_greyhound_data(runner_name: str):
    MIN_RACES = 5

    formatted_name = runner_name.lower().replace(' ', '-').replace("'", "")

    url = f'https://www.thegreyhoundrecorder.com.au/greyhounds/{formatted_name}/'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    tables = pd.read_html(url, storage_options=headers)

    for table in tables:
        if 'Dist' in table.columns and 'Time' in table.columns:
            if len(table) < MIN_RACES:
                print(f"WARNING: less than {MIN_RACES} found!")
            return table
    print(f"WARNING: no race data was found for {runner_name}!")
    return None

def fit_normal_dist(data: pd.DataFrame, race_length: int):
    times = data[data['Dist'] == race_length]['Time']
    return times.mean(), times.std()

def simulate(runner1: tuple[float, float], runner2: tuple[float, float], n_simulations: int = 10000) -> tuple[float, float]:
    runner1_mean, runner1_std = runner1
    runner2_mean, runner2_std = runner2

    wins = {'runner1': 0, 'runner2': 0}
    for _ in range(n_simulations):
        time1 = np.random.normal(runner1_mean, runner1_std)
        time2 = np.random.normal(runner2_mean, runner2_std)
        if time1 < time2:
            wins['runner1'] += 1
        else:
            wins['runner2'] += 1

    return (wins['runner1'] / n_simulations, wins['runner2'] / n_simulations)

def get_user_input():
    runner1_name = input("Enter the name of the first greyhound: ")
    runner2_name = input("Enter the name of the second greyhound: ")
    race_length = int(input("Enter the race length (in meters): "))

    return runner1_name, runner2_name, race_length


if __name__ == "__main__":
    runner1_name, runner2_name, race_length = get_user_input()

    table1 = read_greyhound_data(runner1_name)
    table2 = read_greyhound_data(runner2_name)

    if table1 is None or table2 is None:
        print("ERROR: Unable to retrieve data for one or both greyhounds.")
        exit(1)
    else:
        runner1_params = fit_normal_dist(table1, race_length)
        runner2_params = fit_normal_dist(table2, race_length)

        prob_runner1, prob_runner2 = simulate(runner1_params, runner2_params)
        fair_odds1 = 1 / prob_runner1 if prob_runner1 != 0 else None
        fair_odds2 = 1 / prob_runner2 if prob_runner2 != 0 else None

        print(f"\n-----RESULTS-----")

        print(f"{runner1_name}:")
        print(f"\tFair odds    : {fair_odds1:.2f}")
        print(f"\tWin %        : {prob_runner1:.2f}")
        print(f"\tNo. samples  : {len(table1)}")

        print(f"{runner2_name}:")
        print(f"\tFair odds    : {fair_odds2:.2f}")
        print(f"\tWin %        : {prob_runner2:.2f}")
        print(f"\tNo. samples  : {len(table2)}")
        