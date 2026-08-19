from __future__ import annotations

import json
import math
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
import requests
from scipy.stats import mannwhitneyu, spearmanr

ROOT = Path(__file__).resolve().parents[2]

RAW = ROOT / "data/raw/coinbase/session_days"
PRIVATE_PANEL = (
    ROOT
    / "data/processed/"
    "coinbase_daily_nyse_panel.parquet"
)

OUT_DIR = (
    ROOT
    / "artifacts/multi_venue"
)

SUMMARY_CSV = (
    OUT_DIR
    / "coinbase_pre_post_sensitivity.csv"
)

VALIDATION_JSON = (
    OUT_DIR
    / "coinbase_validation.json"
)

URL = (
    "https://api.exchange.coinbase.com/"
    "products/BTC-USD/candles"
)

START = "2022-01-11"
END = "2026-01-10"
EVENT = pd.Timestamp("2024-01-11").date()

EXCLUDED = {
    pd.Timestamp("2023-03-24").date()
}

RAW.mkdir(
    parents=True,
    exist_ok=True,
)

OUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


calendar = mcal.get_calendar("NYSE")

schedule = calendar.schedule(
    start_date=START,
    end_date=END,
)

session_dates = [
    pd.Timestamp(x).date()
    for x in schedule.index
    if pd.Timestamp(x).date()
    not in EXCLUDED
]


def raw_path(day):
    return (
        RAW
        / f"{day.isoformat()}.json"
    )


def fetch_day(day):
    path = raw_path(day)

    if path.exists():
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        if (
            isinstance(data, list)
            and len(data) >= 288
        ):
            return day, data, "cache"

    day_ts = pd.Timestamp(
        day,
        tz="UTC",
    )

    start = (
        day_ts
        - pd.Timedelta(minutes=5)
    )

    end = (
        day_ts
        + pd.Timedelta(
            hours=23,
            minutes=55,
        )
    )

    params = {
        "granularity": 300,
        "start": start.isoformat(),
        "end": end.isoformat(),
    }

    headers = {
        "User-Agent": (
            "HilmarCorp-Research/"
            "Bitcoin-ETF-Clock"
        )
    }

    last_error = None

    for attempt in range(7):
        try:
            response = requests.get(
                URL,
                params=params,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 429:
                time.sleep(
                    1.5 * (attempt + 1)
                )
                continue

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, list):
                raise RuntimeError(
                    "Unexpected Coinbase payload"
                )

            path.write_text(
                json.dumps(data),
                encoding="utf-8",
            )

            return day, data, "network"

        except Exception as exc:
            last_error = exc
            time.sleep(
                min(
                    8,
                    0.5
                    * (2**attempt),
                )
            )

    raise RuntimeError(
        f"Coinbase fetch failed "
        f"for {day}: {last_error}"
    )


missing_days = [
    day
    for day in session_dates
    if not raw_path(day).exists()
]

print(
    "NYSE sessions requested =",
    len(session_dates),
)

print(
    "Coinbase sessions to fetch =",
    len(missing_days),
)


if missing_days:
    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        futures = {
            executor.submit(
                fetch_day,
                day,
            ): day
            for day in missing_days
        }

        for completed, future in enumerate(
            as_completed(futures),
            start=1,
        ):
            day = futures[future]

            future.result()

            if (
                completed % 50 == 0
                or completed
                == len(missing_days)
            ):
                print(
                    "Coinbase fetched:",
                    completed,
                    "/",
                    len(missing_days),
                )


records = []
quality_exclusions = []


for session_date, sched_row in schedule.iterrows():
    day = pd.Timestamp(
        session_date
    ).date()

    if day in EXCLUDED:
        continue

    path = raw_path(day)

    if not path.exists():
        quality_exclusions.append(
            {
                "date": str(day),
                "reason": (
                    "missing_raw_cache"
                ),
            }
        )
        continue

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    frame = pd.DataFrame(
        raw,
        columns=[
            "timestamp",
            "low",
            "high",
            "open",
            "close",
            "volume",
        ],
    )

    frame["timestamp"] = (
        pd.to_datetime(
            frame["timestamp"],
            unit="s",
            utc=True,
        )
    )

    frame = (
        frame
        .drop_duplicates(
            subset=["timestamp"]
        )
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    frame["close"] = pd.to_numeric(
        frame["close"],
        errors="coerce",
    )

    frame["volume"] = pd.to_numeric(
        frame["volume"],
        errors="coerce",
    )

    frame["lr"] = np.log(
        frame["close"]
    ).diff()

    day_start = pd.Timestamp(
        day,
        tz="UTC",
    )

    day_end = (
        day_start
        + pd.Timedelta(days=1)
    )

    current = frame.loc[
        (
            frame["timestamp"]
            >= day_start
        )
        & (
            frame["timestamp"]
            < day_end
        )
    ].copy()

    if len(current) != 288:
        quality_exclusions.append(
            {
                "date": str(day),
                "reason": (
                    f"daily_bars={len(current)}"
                ),
            }
        )
        continue

    market_open = pd.Timestamp(
        sched_row["market_open"]
    )

    market_close = pd.Timestamp(
        sched_row["market_close"]
    )

    if market_open.tzinfo is None:
        market_open = (
            market_open.tz_localize("UTC")
        )
    else:
        market_open = (
            market_open.tz_convert("UTC")
        )

    if market_close.tzinfo is None:
        market_close = (
            market_close.tz_localize("UTC")
        )
    else:
        market_close = (
            market_close.tz_convert("UTC")
        )

    expected_us_bars = int(
        (
            market_close
            - market_open
        ).total_seconds()
        / 300
    )

    us = current.loc[
        (
            current["timestamp"]
            >= market_open
        )
        & (
            current["timestamp"]
            < market_close
        )
    ]

    if len(us) != expected_us_bars:
        quality_exclusions.append(
            {
                "date": str(day),
                "reason": (
                    "us_bars="
                    f"{len(us)}"
                    "/expected="
                    f"{expected_us_bars}"
                ),
            }
        )
        continue

    volume_total = (
        current["volume"].sum()
    )

    rv_total = (
        current["lr"]
        .pow(2)
        .sum()
    )

    abs_total = (
        current["lr"]
        .abs()
        .sum()
    )

    if not (
        volume_total > 0
        and rv_total > 0
        and abs_total > 0
    ):
        quality_exclusions.append(
            {
                "date": str(day),
                "reason": (
                    "nonpositive_denominator"
                ),
            }
        )
        continue

    records.append(
        {
            "date": pd.Timestamp(day),
            "period": (
                "pre_etf"
                if day < EVENT
                else "post_etf"
            ),
            "expected_us_bars": (
                expected_us_bars
            ),
            "us_bars": len(us),
            "us_volume_share": (
                us["volume"].sum()
                / volume_total
            ),
            "us_variance_share": (
                us["lr"]
                .pow(2)
                .sum()
                / rv_total
            ),
            "us_abs_return_share": (
                us["lr"]
                .abs()
                .sum()
                / abs_total
            ),
        }
    )


panel = pd.DataFrame(records)

panel = (
    panel
    .sort_values("date")
    .reset_index(drop=True)
)

PRIVATE_PANEL.parent.mkdir(
    parents=True,
    exist_ok=True,
)

panel.to_parquet(
    PRIVATE_PANEL,
    index=False,
)


metrics = [
    "us_volume_share",
    "us_variance_share",
    "us_abs_return_share",
]

summary_rows = []


for metric in metrics:
    pre = (
        panel.loc[
            panel["period"]
            == "pre_etf",
            metric,
        ]
        .dropna()
        .to_numpy()
    )

    post = (
        panel.loc[
            panel["period"]
            == "post_etf",
            metric,
        ]
        .dropna()
        .to_numpy()
    )

    mw = mannwhitneyu(
        pre,
        post,
        alternative="two-sided",
    )

    summary_rows.append(
        {
            "metric": metric,
            "pre_n": len(pre),
            "post_n": len(post),
            "pre_median": float(
                np.median(pre)
            ),
            "post_median": float(
                np.median(post)
            ),
            "delta_median_pp": float(
                100
                * (
                    np.median(post)
                    - np.median(pre)
                )
            ),
            "mann_whitney_p": float(
                mw.pvalue
            ),
        }
    )


summary = pd.DataFrame(
    summary_rows
)

summary.to_csv(
    SUMMARY_CSV,
    index=False,
)


binance_summary = pd.read_csv(
    ROOT
    / "artifacts/tables/"
    "pre_post_final.csv"
)

sign_matches = 0

for metric in metrics:
    cb = float(
        summary.loc[
            summary["metric"]
            == metric,
            "delta_median_pp",
        ].iloc[0]
    )

    bn = float(
        binance_summary.loc[
            binance_summary["metric"]
            == metric,
            "delta_median_pp",
        ].iloc[0]
    )

    if math.copysign(
        1.0,
        cb,
    ) == math.copysign(
        1.0,
        bn,
    ):
        sign_matches += 1


binance_panel = pd.read_parquet(
    ROOT
    / "data/processed/"
    "btc_daily_nyse_panel.parquet"
)

binance_panel["date"] = (
    pd.to_datetime(
        binance_panel["date"]
    )
    .dt.tz_localize(None)
    .dt.normalize()
)

panel["date"] = (
    pd.to_datetime(
        panel["date"]
    )
    .dt.tz_localize(None)
    .dt.normalize()
)

merged = panel.merge(
    binance_panel[
        [
            "date",
            "us_volume_share",
        ]
    ].rename(
        columns={
            "us_volume_share": (
                "binance_us_volume_share"
            )
        }
    ),
    on="date",
    how="inner",
)


rho, corr_p = spearmanr(
    merged["us_volume_share"],
    merged[
        "binance_us_volume_share"
    ],
)


volume_row = summary.loc[
    summary["metric"]
    == "us_volume_share"
].iloc[0]


pre_n = int(
    (
        panel["period"]
        == "pre_etf"
    ).sum()
)

post_n = int(
    (
        panel["period"]
        == "post_etf"
    ).sum()
)


required = {
    "pre_sessions_at_least_490": (
        pre_n >= 490
    ),
    "post_sessions_at_least_490": (
        post_n >= 490
    ),
    "positive_volume_shift": (
        float(
            volume_row[
                "delta_median_pp"
            ]
        )
        > 0
    ),
    "volume_shift_mw_p_lt_005": (
        float(
            volume_row[
                "mann_whitney_p"
            ]
        )
        < 0.05
    ),
    "directional_consistency_2_of_3": (
        sign_matches >= 2
    ),
    "cross_venue_daily_volume_rho_gt_035": (
        float(rho) > 0.35
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
        "COINBASE_MULTI_VENUE_SENSITIVITY"
    ),
    "source": (
        "Coinbase Exchange BTC-USD"
    ),
    "frequency": "5m",
    "decision": decision,
    "sessions": {
        "pre": pre_n,
        "post": post_n,
        "quality_exclusions": (
            quality_exclusions
        ),
    },
    "directional_sign_matches": {
        "matched": sign_matches,
        "total": len(metrics),
    },
    "binance_coinbase_volume_share_spearman": {
        "rho": float(rho),
        "p_value": float(corr_p),
        "n": len(merged),
    },
    "required_checks": required,
}


VALIDATION_JSON.write_text(
    json.dumps(
        payload,
        indent=2,
        sort_keys=True,
    )
    + "\n",
    encoding="utf-8",
)


print()
print(
    summary.to_string(
        index=False
    )
)

print()
print(
    "Coinbase/Binance daily "
    "US-volume-share rho =",
    float(rho),
)

print(
    "Directional sign matches =",
    sign_matches,
    "/",
    len(metrics),
)

print(
    "Coinbase multi-venue =",
    decision,
)

if decision != "PASS":
    raise SystemExit(2)

print(
    "PASS_COINBASE_MULTI_VENUE_SENSITIVITY"
)
