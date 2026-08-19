# Data Provenance

## Bitcoin activity

Source:

    Binance Spot BTCUSDT

Frequency:

    5 minutes

Raw study horizon:

    2022-01-11 through 2026-01-10

The source is transformed into a controlled five-minute research dataset and then aggregated by actual NYSE session date.

The primary research is therefore a Binance-market study and should not be represented as direct evidence for every Bitcoin venue.

## NYSE calendar

The US cash-session clock is constructed from `pandas_market_calendars`.

The pipeline uses actual:

- opens;
- closes;
- holidays;
- early closes;
- daylight-saving transitions.

A naive fixed UTC window is not used in the canonical daily panel.

## Source-data exclusion

A single material Bitcoin source gap occurs on March 24, 2023.

The discontinuity includes six missing five-minute observations from 13:30 through 13:55 UTC.

Because the missing observations affect both the NYSE-session numerator and the 24-hour denominator, the complete NYSE session is excluded.

No interpolation or forward filling is used.

## ETF flows

Daily spot-Bitcoin ETF flow observations are obtained from Farside Investors.

The source is treated as a secondary ETF creations/redemptions proxy.

It is not described as a direct measure of aggregate institutional capital flows.

The internal processed source contains observations beyond the publication horizon.

The primary research master panel uses exactly the 501 NYSE post-event sessions through January 9, 2026.

## ETF market activity

Daily ETF OHLCV observations are obtained through `yfinance`.

The validated market universe contains:

    IBIT
    FBTC
    BITB
    ARKB
    BTCO
    EZBC
    BRRR
    HODL
    BTCW
    GBTC
    BTC

The `BTC` mini trust enters the market sample on July 31, 2024.

`MSBT` is present in the flow-source universe but did not have a validated yfinance market cache in the frozen market-turnover reconstruction and is excluded from that turnover aggregation.

## ETF turnover proxy

For each available ETF:

    typical_price
    = (high + low + close) / 3

    dollar_turnover_proxy
    = share_volume × typical_price

The daily cross-fund sum is a trading-intensity proxy.

It is not exact transaction-level dollar volume.

## Public-data boundary

Complete raw and processed third-party market-data files are excluded from public Git history.

The public repository contains derived analytical tables, publication figures, code and evidence manifests.

See `DATA_NOTICE.md`.

## Independent validation sources

### Coinbase Exchange

Coinbase Exchange BTC-USD five-minute candles are used as an independent Bitcoin venue sensitivity layer.

The raw Coinbase observations are retained outside public Git history.

Only aggregate validation statistics are frozen in the public research package.

### Nasdaq

The official BlackRock/iShares IBIT page is used as an independent current-date validation anchor for the market-volume field.

No BlackRock/iShares raw page snapshot is redistributed by this repository.

The public artifact contains only the validation statistics, the source identity and the resulting assurance decision. This is a current-date spot-check, not a full historical vendor certification.
