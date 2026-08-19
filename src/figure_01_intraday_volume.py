from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PATH = "data/processed/btc_5m_etf_clock.parquet"
OUT = Path("outputs/figures")
OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_parquet(PATH)

# For each NY day, compute the share of daily quote volume
daily_total = (
    df.groupby(["date_ny", "period"])["quote_volume"]
      .transform("sum")
)

df["volume_share_day"] = df["quote_volume"] / daily_total

profile = (
    df.groupby(
        ["period", "minute_of_day_ny"],
        as_index=False,
    )["volume_share_day"]
    .mean()
)

# Smooth 30 minutes = 6 x 5m observations
profile["volume_share_smooth"] = (
    profile.groupby("period")["volume_share_day"]
    .transform(
        lambda x: x.rolling(
            6,
            center=True,
            min_periods=1,
        ).mean()
    )
)

fig, ax = plt.subplots(figsize=(11, 5.8))

for period, group in profile.groupby("period"):
    label = {
        "pre_etf": "Avant ETF spot",
        "post_etf": "Après ETF spot",
    }[period]

    ax.plot(
        group["minute_of_day_ny"] / 60,
        group["volume_share_smooth"] * 100,
        label=label,
        linewidth=1.8,
    )

ax.axvline(9.5, linestyle="--", linewidth=1)
ax.axvline(16.0, linestyle="--", linewidth=1)

ax.text(
    9.5,
    ax.get_ylim()[1],
    "  09:30 NY",
    va="top",
    fontsize=9,
)

ax.text(
    16.0,
    ax.get_ylim()[1],
    "  16:00 NY",
    va="top",
    fontsize=9,
)

ax.set_xlim(0, 24)
ax.set_xlabel("Heure de New York")
ax.set_ylabel("Part moyenne du volume quotidien (%)")

ax.set_title(
    "Bitcoin — répartition intrajournalière du volume\n"
    "Avant et après le lancement des ETF spot américains"
)

ax.legend(frameon=False)
ax.grid(alpha=0.2)

fig.tight_layout()

target = OUT / "01_intraday_volume_pre_post.png"
fig.savefig(target, dpi=220)
plt.close(fig)

print(f"Saved -> {target}")
