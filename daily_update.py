from pathlib import Path
from datetime import datetime

from main import main as fetch
from diff import json_to_dict, diff
from settings import min_mcap, num_stocks
from email_funcs import send_email
from credentials import email, password, GOOGLE_APP_CREDS



def daily_update():
    # fetch(email, password)
    results_dir = "results"
    path = Path(results_dir)
    results = [datetime.strptime(file_path.name, "%Y_%m_%d_%H_%M_%S.json") for file_path in path.glob("*.json")]
    results.sort(reverse=True)
    
    old = results[1].strftime("%Y_%m_%d_%H_%M_%S.json")
    new = results[0].strftime("%Y_%m_%d_%H_%M_%S.json")

    old_dict = json_to_dict(f"{results_dir}/{old}")
    new_dict = json_to_dict(f"{results_dir}/{new}")

    added, removed = diff(old_dict, new_dict)

    print(added)
    print(removed)

    change_alert = ""
    if added or removed:
        change_alert = f"""Between the current run ({results[0].strftime('%m/%d/%y %I:%M %p')}) and the last run ({results[1].strftime('%m/%d/%y %I:%M %p')}), the following tickers were

Added - {added}
Removed - {removed}
"""

    stocks = [stock['Ticker'] for stock in new_dict['results']]



    send_email(
        GOOGLE_APP_CREDS["account"],
        GOOGLE_APP_CREDS["password"],
        ["mrtaquito04@gmail.com"],
        f"Magic Formula {datetime.now().strftime('%d/%m/%y %I:%M %p')} Update",
        f"""Zeyn,

{change_alert}
Joel Greenblatt's Magic Formula currently recommends the following stocks:
Min Market Cap = ${min_mcap}M
Number of Stocks = {num_stocks}
{'\n'.join(stocks)}

-ZMagicFormulaInvestingScraper
        """,
        [f"{results_dir}/{results[0].strftime('%Y_%m_%d_%H_%M_%S.csv')}"]
    )




if __name__ == "__main__":
    daily_update()