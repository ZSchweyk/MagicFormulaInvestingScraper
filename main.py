import argparse
import csv
from datetime import datetime
import json
import os
import sys
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from settings import min_mcap, num_stocks


LOGIN_URL = "https://www.magicformulainvesting.com/Account/LogOn"
SCREENER_URL = "https://www.magicformulainvesting.com/Screening/StockScreening"


@dataclass
class Args:
    min_mcap_millions: int
    num_stocks: int
    headless: bool
    out_json: str
    out_csv: str
    timeout_ms: int


def require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise SystemExit(f"Missing env var {name}. Example:\n  set {name}=you@example.com")
    return val


def _strip_wrapping_quotes(s: str) -> str:
    s = (s or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        s = s[1:-1].strip()
    return s

def login_if_needed(page, email: str, password: str, timeout_ms: int = 30000) -> None:
    """
    Go to screener. If redirected to login, log in using inputs:
      - input#Email
      - input#Password
    """
    email = _strip_wrapping_quotes(email)
    password = _strip_wrapping_quotes(password)

    page.goto(SCREENER_URL, wait_until="domcontentloaded", timeout=timeout_ms)

    # If already logged in, we're done
    if "/Account/LogOn" not in page.url:
        return

    # Wait for login inputs
    email_input = page.locator("input#Email")
    pass_input  = page.locator("input#Password")

    email_input.wait_for(state="visible", timeout=timeout_ms)
    pass_input.wait_for(state="visible", timeout=timeout_ms)

    # Fill
    email_input.fill(email)
    pass_input.fill(password)

    # Optional sanity check (helps catch hidden/overlaid inputs)
    try:
        filled = email_input.input_value()
        if filled.strip() != email.strip():
            raise RuntimeError(f"Email field didn't take the value. DOM has: {filled!r}")
    except Exception:
        # input_value can fail on some custom fields; ignore
        pass

    # Submit
    # Prefer actual submit controls, otherwise press Enter
    submit = page.locator("input[type=submit], button[type=submit]")
    if submit.count() > 0:
        submit.first.click()
    else:
        pass_input.press("Enter")

    # Wait for redirect back to screener
    try:
        page.wait_for_url("**/Screening/StockScreening", timeout=timeout_ms)
    except PWTimeoutError:
        # Pull any validation message to explain what happened
        validation_text = " ".join(
            t.strip()
            for t in page.locator(
                ".validation-summary-errors, .field-validation-error, .validation-summary-valid"
            ).all_text_contents()
            if t.strip()
        )
        raise RuntimeError(
            f"Login did not reach screener (still at {page.url}). "
            f"Validation: {validation_text or '(none found)'}"
        )

    


from playwright.sync_api import TimeoutError as PWTimeoutError

def set_filters_and_submit(page, min_mcap_millions: int, num_stocks: int, timeout_ms: int) -> None:
    # Fill Minimum Market Cap (million)
    # We try multiple strategies because the exact input attributes can change.
    filled = False

    # Strategy A: find textbox near the "Minimum Market Cap" text
    try:
        # Grab first textbox on page (often the market cap box on this simple form)
        page.get_by_role("textbox").first.fill(str(min_mcap_millions))
        filled = True
    except Exception:
        pass

    if not filled:
        # Strategy B: label-based (if the input has an accessible label)
        try:
            page.get_by_label("Minimum Market Cap").fill(str(min_mcap_millions))
            filled = True
        except Exception:
            pass

    if not filled:
        raise RuntimeError("Could not find the Minimum Market Cap input. Use Playwright inspector to update selectors.")

    # Select Number of Stocks (30 or 50)
    if num_stocks not in (30, 50):
        raise ValueError("num_stocks must be 30 or 50.")

    selected = False

    # --- FIX: site bug/oddity: both radios share id="Select30"
    # 30 radio has value="true"; 50 radio has value="false"
    try:
        target_value = "true" if num_stocks == 30 else "false"
        radio = page.locator(f"input#Select30[value='{target_value}']")

        # Ensure we actually matched something visible
        radio.first.wait_for(state="visible", timeout=timeout_ms)

        # Use check() (best for radios); fallback to click if needed
        try:
            radio.first.check(force=True)
        except Exception:
            radio.first.click(force=True)

        # Verify selection stuck (some pages ignore synthetic clicks)
        try:
            if not radio.first.is_checked():
                raise RuntimeError("Radio did not become checked.")
        except Exception:
            # If is_checked isn't supported (non-radio), verify checked property
            checked = radio.first.evaluate("el => !!el.checked")
            if not checked:
                raise RuntimeError("Radio did not become checked (el.checked false).")

        selected = True
    except Exception:
        selected = False

    # Strategy B: if it’s a <select> (less likely), try select_option
    if not selected:
        try:
            page.locator("select").first.select_option(str(num_stocks))
            selected = True
        except Exception:
            pass

    if not selected:
        raise RuntimeError("Could not select Number of Stocks (30/50). Update selectors with Playwright inspector.")

    # Submit the screener form.
    # We try common button texts; otherwise submit by pressing Enter.
    submitted = False
    for btn_text in ["Get Stocks", "Screen", "Submit", "Search", "Go"]:
        try:
            page.get_by_role("button", name=btn_text).click(timeout=1000)
            submitted = True
            break
        except Exception:
            continue

    if not submitted:
        # Sometimes it’s an <input type="submit"> without role=button name we expect
        try:
            page.locator("input[type=submit]").first.click(timeout=1000)
            submitted = True
        except Exception:
            pass

    if not submitted:
        # Last resort: press Enter in the market cap box
        page.get_by_role("textbox").first.press("Enter")

    # Wait for results to appear (your real results table is inside #tableform)
    try:
        page.wait_for_selector("div#tableform table", timeout=timeout_ms)
    except PWTimeoutError:
        raise RuntimeError("No results table found after submitting (div#tableform table). The page layout may have changed.")



def scrape_tableform_table(page, timeout_ms: int = 30000) -> List[Dict[str, Any]]:
    """
    Scrape the table contained within <div id="tableform"> ... <table> ... </table> ... </div>
    Returns list of dict rows keyed by table headers.
    """
    wrapper = page.locator("div#tableform")
    wrapper.wait_for(state="attached", timeout=timeout_ms)

    table = wrapper.locator("table").first
    table.wait_for(state="visible", timeout=timeout_ms)

    # ---- Headers
    headers = table.locator("thead tr th").all_text_contents()
    headers = [h.strip() for h in headers if h and h.strip()]

    # Fallback if no thead
    if not headers:
        header_cells = table.locator("tr").first.locator("th,td").all_text_contents()
        headers = [c.strip() for c in header_cells if c and c.strip()]

    # ---- Rows
    rows_out: List[Dict[str, Any]] = []

    body_rows = table.locator("tbody tr")
    if body_rows.count() == 0:
        # fallback: all rows, skipping the first if we used it as header
        body_rows = table.locator("tr")
        start_idx = 1 if headers else 0
    else:
        start_idx = 0

    for i in range(start_idx, body_rows.count()):
        tr = body_rows.nth(i)
        cells = [c.strip() for c in tr.locator("td").all_text_contents()]
        if not cells:
            continue

        if headers and len(headers) == len(cells):
            row = {headers[j]: cells[j] for j in range(len(headers))}
        else:
            # mismatched columns -> keep raw with generic keys + include headers if present
            row = {f"col_{j+1}": cells[j] for j in range(len(cells))}
            if headers:
                row["_headers"] = headers

        rows_out.append(row)

    return rows_out

# def scrape_first_table(page) -> List[Dict[str, Any]]:
#     # Scrape the first table on the page into a list of dict rows.
#     table = page.locator("table").first

#     # Extract headers
#     headers = table.locator("thead tr th").all_text_contents()
#     headers = [h.strip() for h in headers if h.strip()]

#     # If there is no thead, fall back to first row as header guess
#     if not headers:
#         first_row_cells = table.locator("tr").first.locator("th,td").all_text_contents()
#         headers = [c.strip() for c in first_row_cells]

#     # Extract body rows
#     rows = []
#     # Prefer tbody rows; fallback to all tr (minus header-like first row if needed)
#     body_rows = table.locator("tbody tr")
#     if body_rows.count() == 0:
#         body_rows = table.locator("tr")

#     for i in range(body_rows.count()):
#         tr = body_rows.nth(i)
#         cells = [c.strip() for c in tr.locator("td").all_text_contents()]
#         # skip header-only rows or empties
#         if not cells:
#             continue

#         if headers and len(headers) == len(cells):
#             row = {headers[j]: cells[j] for j in range(len(headers))}
#         else:
#             # If column mismatch, store as generic columns
#             row = {f"col_{j+1}": cells[j] for j in range(len(cells))}
#         rows.append(row)

#     return rows


def write_outputs(
    rows: List[Dict[str, Any]],
    out_json: str,
    out_csv: str,
    *,
    min_mcap_millions: int,
    num_stocks: int
) -> None:
    payload = {
        "inputs": {
            "min_market_cap_millions": min_mcap_millions,
            "num_stocks": num_stocks,
            "scrape_timestamp": datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            "source": "magicformulainvesting.com"
        },
        "results": rows
    }

    # ---- JSON
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    # ---- CSV (still just the rows, not metadata)
    keys = sorted({k for r in rows for k in r.keys()})
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)



def parse_args() -> Args:
    now_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    p = argparse.ArgumentParser()
    p.add_argument("--min-mcap", type=int, default=min_mcap, help="Minimum market cap in *millions* (e.g., 1000 = $1B).")
    p.add_argument("--num-stocks", type=int, default=num_stocks, help="Number of stocks to list (30 or 50).")
    p.add_argument("--headless", action="store_true", default=True, help="Run browser headless.")
    p.add_argument("--out-json", default=f"results/{now_str}.json")
    p.add_argument("--out-csv", default=f"results/{now_str}.csv")
    p.add_argument("--timeout-ms", type=int, default=30000)
    a = p.parse_args()

    return Args(
        min_mcap_millions=a.min_mcap,
        num_stocks=a.num_stocks,
        headless=a.headless,
        out_json=a.out_json,
        out_csv=a.out_csv,
        timeout_ms=a.timeout_ms,
    )


def main(_email=None, _password=None) -> None:
    args = parse_args()
    email = _email if _email is not None else require_env("MFI_EMAIL") 
    password = _password if _password is not None else require_env("MFI_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()

        login_if_needed(page, email, password, args.timeout_ms)
        set_filters_and_submit(
            page,
            args.min_mcap_millions,
            args.num_stocks,
            args.timeout_ms
        )

        rows = scrape_tableform_table(page)
        if not rows:
            raise RuntimeError("Scrape succeeded but found 0 rows in the first table. You may need a more specific table selector.")

        # input("Press Enter to continue and save outputs...")
        write_outputs(
            rows,
            args.out_json,
            args.out_csv,
            min_mcap_millions=args.min_mcap_millions,
            num_stocks=args.num_stocks
        )


        print(f"Saved {len(rows)} rows to:\n  {args.out_json}\n  {args.out_csv}")
        browser.close()
        return args.out_json


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
