from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]

OUT = (
    ROOT
    / "artifacts/source_validation/"
    "blackrock_ibit_current_volume_validation.json"
)

OUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

URL = (
    "https://www.ishares.com/us/products/"
    "333011/ishares-bitcoin-trust-etf"
)

headers = {
    "User-Agent": (
        "Mozilla/5.0 "
        "HilmarCorp-Research/"
        "Bitcoin-ETF-Clock"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

response = requests.get(
    URL,
    headers=headers,
    timeout=30,
)

response.raise_for_status()

html = response.text

text = re.sub(
    r"<script.*?</script>",
    " ",
    html,
    flags=re.I | re.S,
)

text = re.sub(
    r"<style.*?</style>",
    " ",
    text,
    flags=re.I | re.S,
)

text = re.sub(
    r"<[^>]+>",
    " ",
    text,
)

text = unescape(text)

text = re.sub(
    r"\s+",
    " ",
    text,
).strip()


def parse_number(value: str) -> float:
    return float(
        value.replace(",", "")
    )


volume_match = re.search(
    r"Daily Volume\s*"
    r"\$?\s*"
    r"([0-9][0-9,]*(?:\.[0-9]+)?)"
    r"\s*as of\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    text,
    flags=re.I,
)

if volume_match is None:
    raise SystemExit(
        "BlackRock Daily Volume not found"
    )


official_volume = parse_number(
    volume_match.group(1)
)

date_text = volume_match.group(2)

official_date = None

for fmt in (
    "%b %d, %Y",
    "%B %d, %Y",
):
    try:
        official_date = datetime.strptime(
            date_text,
            fmt,
        ).date()
        break
    except ValueError:
        pass

if official_date is None:
    raise SystemExit(
        f"Could not parse BlackRock date: "
        f"{date_text}"
    )


exchange_match = re.search(
    r"Exchange\s+([A-Za-z0-9 ]+?)"
    r"\s+(?:Benchmark Index|Indicative Basket)",
    text,
    flags=re.I,
)

exchange = (
    exchange_match.group(1).strip()
    if exchange_match
    else None
)


avg_match = re.search(
    r"30 Day Avg\.?\s*Volume\s*"
    r"\$?\s*"
    r"([0-9][0-9,]*(?:\.[0-9]+)?)"
    r"\s*as of\s*"
    r"([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    text,
    flags=re.I,
)

official_avg_30 = (
    parse_number(
        avg_match.group(1)
    )
    if avg_match
    else None
)


start = (
    official_date
    - timedelta(days=70)
)

end = (
    official_date
    + timedelta(days=2)
)


market = yf.download(
    "IBIT",
    start=start.isoformat(),
    end=end.isoformat(),
    auto_adjust=False,
    progress=False,
    actions=False,
)


if market.empty:
    raise SystemExit(
        "yfinance returned no IBIT data"
    )


if isinstance(
    market.columns,
    pd.MultiIndex,
):
    market.columns = [
        str(col[0]).lower()
        for col in market.columns
    ]
else:
    market.columns = [
        str(col).lower()
        for col in market.columns
    ]


market = market.reset_index()

date_col = next(
    col
    for col in market.columns
    if str(col).lower() == "date"
)

volume_col = next(
    col
    for col in market.columns
    if str(col).lower() == "volume"
)


market[date_col] = pd.to_datetime(
    market[date_col]
).dt.date

market[volume_col] = pd.to_numeric(
    market[volume_col],
    errors="coerce",
)


same_day = market.loc[
    market[date_col]
    == official_date
]

if len(same_day) != 1:
    raise SystemExit(
        "Could not resolve exactly one "
        "yfinance IBIT observation for "
        f"{official_date}"
    )


yahoo_volume = float(
    same_day[volume_col].iloc[0]
)


relative_difference = float(
    abs(
        yahoo_volume
        - official_volume
    )
    / max(
        abs(official_volume),
        1.0,
    )
)


history_to_date = (
    market.loc[
        market[date_col]
        <= official_date
    ]
    .dropna(
        subset=[volume_col]
    )
    .sort_values(date_col)
)


last_30 = (
    history_to_date
    .tail(30)[volume_col]
    .astype(float)
)


yahoo_avg_30 = (
    float(last_30.mean())
    if len(last_30) == 30
    else None
)


avg_30_relative_difference = (
    float(
        abs(
            yahoo_avg_30
            - official_avg_30
        )
        / max(
            abs(official_avg_30),
            1.0,
        )
    )
    if (
        yahoo_avg_30 is not None
        and official_avg_30 is not None
    )
    else None
)


required = {
    "issuer_page_resolved": True,
    "official_daily_volume_positive": (
        official_volume > 0
    ),
    "yfinance_daily_volume_positive": (
        yahoo_volume > 0
    ),
    "daily_volume_relative_difference_le_1pct": (
        relative_difference <= 0.01
    ),
    "exchange_is_nasdaq": (
        exchange is not None
        and "NASDAQ" in exchange.upper()
    ),
}


decision = (
    "PASS"
    if all(required.values())
    else "FAIL"
)


payload = {
    "study_id": (
        "HILMARCORP-BITCOIN-ETF-CLOCK"
    ),
    "control": (
        "ETF_MARKET_SOURCE_SPOT_CHECK"
    ),
    "instrument": "IBIT",
    "issuer": "BlackRock / iShares",
    "official_source_url": URL,
    "secondary_source": (
        "Yahoo Finance via yfinance"
    ),
    "scope": (
        "Current-date source spot-check. "
        "This control does not claim "
        "full historical vendor validation."
    ),
    "decision": decision,
    "official_date": str(
        official_date
    ),
    "official_exchange": exchange,
    "official_daily_volume": (
        official_volume
    ),
    "yfinance_daily_volume": (
        yahoo_volume
    ),
    "daily_volume_relative_difference": (
        relative_difference
    ),
    "official_30d_avg_volume": (
        official_avg_30
    ),
    "yfinance_30_session_avg_volume": (
        yahoo_avg_30
    ),
    "avg_30_relative_difference": (
        avg_30_relative_difference
    ),
    "required_checks": required,
    "interpretation": (
        "Independent issuer-level "
        "spot validation of the market-"
        "volume field used by the "
        "secondary yfinance acquisition "
        "layer. Production asset-management "
        "usage should use an appropriately "
        "licensed market-data source."
    ),
}


OUT.write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


print(
    "BlackRock date =",
    official_date,
)

print(
    "BlackRock Daily Volume =",
    official_volume,
)

print(
    "yfinance Volume =",
    yahoo_volume,
)

print(
    "relative difference =",
    relative_difference,
)

print(
    "exchange =",
    exchange,
)

if official_avg_30 is not None:
    print(
        "BlackRock 30d avg =",
        official_avg_30,
    )

if yahoo_avg_30 is not None:
    print(
        "yfinance 30-session avg =",
        yahoo_avg_30,
    )

print(
    "ETF source spot-check =",
    decision,
)

if decision != "PASS":
    raise SystemExit(2)

print(
    "PASS_ETF_MARKET_SOURCE_SPOT_CHECK"
)
