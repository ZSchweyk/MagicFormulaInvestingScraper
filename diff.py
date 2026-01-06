import json
from pprint import pprint


def diff(dict1, dict2):
    set1 = set([stock["Ticker"] for stock in dict1["results"]])
    set2 = set([stock["Ticker"] for stock in dict2["results"]])

    added_tickers = set2 - set1
    removed_tickers = set1 - set2
    
    return added_tickers, removed_tickers

def json_to_dict(file1):
    try:
        with open(file1, 'r', encoding='utf-8') as file:
            data = json.load(file)
            
        return data
    except FileNotFoundError:
        print(f"Error: File '{file1}' could not be found.")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{file1}'.")



if __name__ == "__main__":
    data1 = json_to_dict("results/results-2025_12_31_12_42_25.json")
    data2 = json_to_dict("results/results-2026_01_05_19_03_17.json")
    d = diff(data1, data2)
    pprint(d)

    a = {"a", "b", "c"}
    b = {"a", "b", "d"}

    print(a - b)
    print(b - a)
