import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

def read_greyhound_data(runner_name: str, race_length, race_date) -> pd.DataFrame:
    """
    Fetches racing data for a given greyhound from The Greyhound Recorder website.

    ### Parameters
    - runner_name : str
        - name of the runner

    ### Returns
    - output : pd.DataFrame
        - DataFrame containing race data including 'Dist' and 'Time' columns, or None if data is insufficient
    """
    MIN_RACES = 5

    formatted_name = runner_name.lower().replace(' ', '-').replace("'", "")

    url = f'https://www.thegreyhoundrecorder.com.au/greyhounds/{formatted_name}/'

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    tables = pd.read_html(url, storage_options=headers)

    for table in tables:
        if 'Dist' in table.columns and 'Time' in table.columns:
            table['Date'] = (pd.to_datetime(table['Date'], format="%d/%m/%y").dt.strftime("%Y-%m-%d"))
            table = table[table['Date'] < race_date]
            table = table[table['Dist'] == race_length]
            if len(table) < MIN_RACES:
                print(f"WARNING: less than {MIN_RACES} found!")
            return table
    print(f"WARNING: no race data was found for {runner_name}!")
    return pd.DataFrame(None)

def fit_normal_dist(data: pd.DataFrame) -> tuple[float, float]:
    """
    Fits the race times for a given distance to a normal distribution.
    """
    times = data['Time']
    return times.mean(), times.std()

def simulate(runner1: tuple[float, float], runner2: tuple[float, float], n_simulations: int = 10000) -> tuple[float, float]:
    """
    Simulates `n_simulations` races between two greyhounds based on their normal distribution parameters.

    ### Parameters
    - runner1 : tuple[float, float]
        - mean and std of runner 1
    - runner2 : tuple[float, float]
        - mean and std of runner 2

    ### Returns
    - output : tuple[float, float]
        - probability of runner 1 winning, probability of runner 2 winning
    """
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

    return wins['runner1'] / n_simulations, wins['runner2'] / n_simulations

def get_user_input():
    """
    Prompts the user for input for runner names and distance
    """
    runner1_name = input("Enter the name of the first greyhound: ")
    runner2_name = input("Enter the name of the second greyhound: ")
    race_length = int(input("Enter the race length (in meters): "))
    race_date = input("Enter the race date (YYYY-MM-DD) [default: today]: ").strip() or datetime.today().strftime("%Y-%m-%d")
    return runner1_name, runner2_name, race_length, race_date

def calculate_ev(fair_odds: float, offered_odds: float, commission: float = 0.08) -> float:
    """
    Calculates the expected value of a bet.

    ### Parameters
    - fair_odds : float
        - the fair odds of the outcome
    - offered_odds : float
        - the odds being offered by the bookmaker

    ### Returns
    - output : float
        - expected value of the bet
    """
    if commission >= 1:
        commission /= 100
    
    effective_offered_odds = (offered_odds - 1) * (1 - commission) + 1

    return effective_offered_odds / fair_odds - 1


if __name__ == "__main__":
    runner1_name, runner2_name, race_length, race_date = get_user_input()

    table1 = read_greyhound_data(runner1_name, race_length, race_date)
    table2 = read_greyhound_data(runner2_name, race_length, race_date)

    if table1 is None or table2 is None:
        print("ERROR: Unable to retrieve data for one or both greyhounds.")
        exit(1)
    else:
        runner1_params = fit_normal_dist(table1)
        runner2_params = fit_normal_dist(table2)

        prob_runner1, prob_runner2 = simulate(runner1_params, runner2_params)
        fair_odds1 = 1 / prob_runner1 if prob_runner1 != 0 else None
        fair_odds2 = 1 / prob_runner2 if prob_runner2 != 0 else None

        print(f"\n-----RESULTS-----")

        print(f"{runner1_name}:")
        print(f"\tFair odds    : {fair_odds1:.2f}")
        print(f"\tWin %        : {100*prob_runner1:.2f}")
        print(f"\tNo. samples  : {len(table1)}")

        print(f"{runner2_name}:")
        print(f"\tFair odds    : {fair_odds2:.2f}")
        print(f"\tWin %        : {100*prob_runner2:.2f}")
        print(f"\tNo. samples  : {len(table2)}")
        