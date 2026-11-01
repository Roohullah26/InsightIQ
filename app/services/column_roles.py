"""Semantic column-role detection shared by the profiler, insights engine, and Copilot.

Separates identifier columns (customer IDs, UUIDs, zip codes, ...) from real business
measures and dimensions so identifiers are never summed, averaged, correlated, or
flagged as outliers.
"""

import re
from typing import Any

import numpy as np
import pandas as pd

IDENTIFIER_NAME_PATTERN = re.compile(r"\b(id|uuid|guid|index|key|code|zip|phone)\b", re.IGNORECASE)

# Ordered by business priority: earlier patterns win when choosing the default measure.
MEASURE_PRIORITY_PATTERNS: list[str] = [
    r"total\s*spend",
    r"revenue",
    r"sales",
    r"profit",
    r"amount",
    r"spend",
    r"items?\s*purchased",
    r"purchase",
    r"income",
    r"quantity",
    r"units?",
    r"score",
    r"price",
    r"cost",
]

DIMENSION_PRIORITY_PATTERNS: list[str] = [
    r"region",
    r"city",
    r"category",
    r"segment",
    r"channel",
    r"department",
    r"product",
    r"type",
    r"tier",
    r"gender",
    r"state",
    r"country",
]


def normalize_name(name: Any) -> str:
    """Lower-case a column name, splitting camelCase and treating `_`/`-` as spaces."""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name))
    return re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()


def _is_sequential_integers(series: pd.Series) -> bool:
    """True if the column is 100% unique integers increasing by exactly 1 (e.g. row IDs)."""
    clean = series.dropna()
    if len(clean) < 3 or len(clean) != len(series):
        return False
    if not pd.api.types.is_numeric_dtype(clean) or pd.api.types.is_bool_dtype(clean):
        return False
    values = clean.to_numpy(dtype=float)
    if not np.all(np.equal(np.mod(values, 1), 0)):
        return False
    if len(np.unique(values)) != len(values):
        return False
    diffs = np.diff(np.sort(values))
    return bool(np.all(diffs == 1))


def is_identifier_column(series: pd.Series, name: Any = None) -> bool:
    """Detect identifier columns by name pattern or by sequential unique integers."""
    col_name = name if name is not None else series.name
    normalized = normalize_name(col_name)

    if _is_sequential_integers(series):
        return True

    if IDENTIFIER_NAME_PATTERN.search(normalized):
        if not pd.api.types.is_numeric_dtype(series) or pd.api.types.is_bool_dtype(series):
            return True
        # Numeric columns named "...index" with real fractional values are metrics, not IDs.
        clean = series.dropna()
        if clean.empty:
            return True
        return bool(np.all(np.equal(np.mod(clean.to_numpy(dtype=float), 1), 0)))
    return False


def _priority(name: str, patterns: list[str]) -> int:
    normalized = normalize_name(name)
    for idx, pattern in enumerate(patterns):
        if re.search(pattern, normalized):
            return idx
    return len(patterns)


def classify_columns(df: pd.DataFrame) -> dict[str, Any]:
    """Split DataFrame columns into identifiers, measures, and dimensions.

    Returns a dict with: identifiers, measures (priority ordered), dimensions (usefulness ordered),
    primary_measure, primary_dimension, secondary_dimension.
    """
    identifiers: list[str] = []
    measures: list[str] = []
    dimensions: list[str] = []

    for col in df.columns:
        series = df[col]
        if is_identifier_column(series, col):
            identifiers.append(str(col))
        elif pd.api.types.is_bool_dtype(series):
            continue
        elif pd.api.types.is_numeric_dtype(series):
            measures.append(str(col))
        elif not pd.api.types.is_datetime64_any_dtype(series) and (
            series.dtype == object
            or pd.api.types.is_string_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            dimensions.append(str(col))

    # Stable sort keeps original order among equal priority.
    measures.sort(key=lambda c: _priority(c, MEASURE_PRIORITY_PATTERNS))

    total_rows = len(df)

    def dim_key(col: str) -> tuple[int, int, int]:
        nunique = int(df[col].nunique(dropna=True))
        useful = 2 <= nunique <= 50 and nunique < max(total_rows, 2)
        return (0 if useful else 1, _priority(col, DIMENSION_PRIORITY_PATTERNS), nunique)

    dimensions.sort(key=dim_key)

    return {
        "identifiers": identifiers,
        "measures": measures,
        "dimensions": dimensions,
        "primary_measure": measures[0] if measures else None,
        "primary_dimension": dimensions[0] if dimensions else None,
        "secondary_dimension": dimensions[1] if len(dimensions) > 1 else None,
    }
