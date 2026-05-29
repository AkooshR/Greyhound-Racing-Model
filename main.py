import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import requests
from io import StringIO
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

MIN_RACES = 5
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

    formatted_name = runner_name.lower().replace(' ', '-').replace("'", "")

    url = f'https://www.thegreyhoundrecorder.com.au/greyhounds/{formatted_name}/'

    # Use a requests Session with retries and realistic browser headers
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.google.com/',
        'Connection': 'keep-alive',
    }

    try:
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code == 403:
            # Try cloudscraper fallback if available (handles some bot protections)
            try:
                import cloudscraper
                scraper = cloudscraper.create_scraper()
                resp = scraper.get(url, headers=headers, timeout=10)
            except Exception:
                pass

        resp.raise_for_status()
        tables = pd.read_html(StringIO(resp.text))
    except requests.HTTPError as e:
        status = getattr(e.response, 'status_code', 'N/A')
        snippet = (e.response.text[:500] if getattr(e.response, 'text', None) else '')
        print(f"WARNING: failed to fetch data for {runner_name} ({status} {e})")
        if snippet:
            print(f"Response snippet: {snippet!s}")
        return pd.DataFrame()
    except Exception as e:
        print(f"WARNING: failed to fetch data for {runner_name} ({e})")
        return pd.DataFrame()

    for table in tables:
        if 'Dist' in table.columns and 'Time' in table.columns:
            table['Date'] = (pd.to_datetime(table['Date'], format="%d/%m/%y").dt.strftime("%Y-%m-%d"))
            table = table[table['Date'] < race_date]
            table = table[table['Dist'] == race_length]
            if len(table) < MIN_RACES:
                print(f"WARNING: less than {MIN_RACES} found!")
                pass
            return table
    print(f"WARNING: no race data was found for {runner_name}!")
    return pd.DataFrame(None)

def fit_normal_dist(data: pd.DataFrame) -> tuple[float, float]:
    """
    Fits the race times for a given distance to a normal distribution.
    """
    times = data['Time']
    return times.mean(), times.std()

def simulate(runner1: tuple[float, float], runner2: tuple[float, float], n_simulations: int = 5000) -> tuple[float, float]:
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

def runner_analysis(runner1_name, runner2_name, race_length, race_date) -> tuple[tuple[float, float], bool]:
    """
    Void function that prints out the model's predicted fair odds and win %, as well as
    the number of samples and mean time for each runner.
    
    :param runner1_name: Description
    :param runner2_name: Description
    :param race_length: Description
    :param race_date: Description
    """
    table1 = read_greyhound_data(runner1_name, race_length, race_date)
    table2 = read_greyhound_data(runner2_name, race_length, race_date)

    fair_odds1, fair_odds2 = 0.0, 0.0

    if table1.shape[0] in (0, 1) or table2.shape[0] in (0, 1):
        print("ERROR: Unable to retrieve data for one or both greyhounds.")
        pass
    else:
        runner1_params = fit_normal_dist(table1)
        runner2_params = fit_normal_dist(table2)

        prob_runner1, prob_runner2 = simulate(runner1_params, runner2_params)
        fair_odds1 = 1 / prob_runner1 if prob_runner1 != 0 else 0.0
        fair_odds2 = 1 / prob_runner2 if prob_runner2 != 0 else 0.0

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

    return (fair_odds1, fair_odds2), (len(table1) >= 5 and len(table2) >= 5)

if __name__ == "__main__":
    runner1_name, runner2_name, race_length, race_date = get_user_input()

    runner_analysis(runner1_name, runner2_name, race_length, race_date)
