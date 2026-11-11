"""Model price table and cost arithmetic.

Source: Anthropic pricing documentation, read 2026-11-11.

Prices are USD per million tokens. Discounts are expressed as multipliers on the
input price: a cache read costs 0.1x, a 5-minute cache write costs 1.25x, and a
batch request costs 0.5x in both directions.

Conventions used by :func:`price`:

* ``tokens_in`` counts prompt tokens that were NOT served from the cache
  (the API's ``input_tokens``); ``cached`` counts cache-read tokens on top.
* Tiered models pick their tier from the whole prompt
  (``tokens_in + cached + cache_write``) and apply it to the whole request.
"""
from __future__ import annotations

# Each model maps to a list of (max_prompt_tokens, input_per_mtok, output_per_mtok)
# tiers, checked in order; ``None`` as the bound means "no upper limit".
# A model set to None has no verified price.
PRICES: dict[str, dict] = {
    "anthropic-2026-11": {
        "batch_multiplier": 0.5,
        "cache_read_multiplier": 0.1,
        "cache_write_5m_multiplier": 1.25,
        "models": {
            "claude-haiku-5-5": [(100_000, 0.10, 0.50), (None, 0.50, 2.50)],
            "claude-sonnet-5-5": [(None, 2.0, 10.0)],
            "claude-opus-5-5": None,  # not verified
        },
    }
}


def price(
    model: str,
    tokens_in: int,
    tokens_out: int,
    cached: int = 0,
    batch: bool = False,
    table: str = "anthropic-2026-11",
    cache_write: int = 0,
) -> float:
    """Cost in USD of one request. Unknown or unverified models raise KeyError."""
    spec = PRICES[table]
    tiers = spec["models"].get(model)
    if tiers is None:
        raise KeyError(f"no verified price for model {model!r} in table {table!r}")
    prompt_tokens = tokens_in + cached + cache_write
    rate_in = rate_out = 0.0
    for bound, p_in, p_out in tiers:
        if bound is None or prompt_tokens <= bound:
            rate_in, rate_out = p_in, p_out
            break
    usd = (
        tokens_in * rate_in
        + cached * rate_in * spec["cache_read_multiplier"]
        + cache_write * rate_in * spec["cache_write_5m_multiplier"]
        + tokens_out * rate_out
    ) / 1_000_000
    if batch:
        usd *= spec["batch_multiplier"]
    return usd
