"""
validator.py
------------
Validation phase of the ETL pipeline.

Checks that the DataFrame produced by standardizer.py respects
the WoS column schema before it gets passed to the dashboard.

Main entry point:
    validate(df) → pd.DataFrame
"""

import pandas as pd

# All mandatory columns and their expected types
MANDATORY_COLUMNS = {
    "DB":   str,
    "UT":   str,
    "DI":   str,
    "PMID": str,
    "TI":   str,
    "SO":   str,
    "JI":   str,
    "PY":   str,
    "DT":   str,
    "LA":   str,
    "TC":   int,
    "AU":   list,
    "AF":   list,
    "C1":   list,
    "RP":   str,
    "CR":   list,
    "DE":   list,
    "ID":   list,
    "AB":   str,
    "VL":   str,
    "IS":   str,
    "BP":   str,
    "EP":   str,
    "SR":   str,
}


def check_columns(df: pd.DataFrame) -> list:
    """
    Checks that all mandatory columns are present in the DataFrame.
    Returns a list of missing column names.
    """
    missing = []
    for col in MANDATORY_COLUMNS:
        if col not in df.columns:
            missing.append(col)
    return missing


def check_nulls(df: pd.DataFrame) -> list:
    """
    Checks that no cell contains None or NaN.
    Returns a list of column names that contain null values.
    """
    offending = []
    for col in MANDATORY_COLUMNS:
        if col not in df.columns:
            continue
        has_null = df[col].apply(lambda x: x is None or (isinstance(x, float) and pd.isna(x))).any()
        if has_null:
            offending.append(col)
    return offending


def check_types(df: pd.DataFrame) -> list:
    """
    Checks that each column contains the correct Python type.
    Returns a list of column names where the type is wrong.
    """
    offending = []
    for col, expected_type in MANDATORY_COLUMNS.items():
        if col not in df.columns:
            continue
        wrong = df[col].apply(lambda x: not isinstance(x, expected_type)).any()
        if wrong:
            offending.append(col)
    return offending



def validate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Main entry point for the validator.
    Runs all checks on the DataFrame and prints a report.
    Raises a ValueError if any check fails.
    Returns the DataFrame unchanged if all checks pass.
    """
    print("Running validation...")
    passed = True

    missing_cols = check_columns(df)
    if missing_cols:
        print(f"  FAIL — missing columns: {missing_cols}")
        passed = False
    else:
        print("  PASS — all mandatory columns present")

    null_cols = check_nulls(df)
    if null_cols:
        print(f"  FAIL — null values found in: {null_cols}")
        passed = False
    else:
        print("  PASS — no null values found")

    type_cols = check_types(df)
    if type_cols:
        print(f"  FAIL — wrong types in: {type_cols}")
        passed = False
    else:
        print("  PASS — all column types correct")

    if not passed:
        raise ValueError("Validation failed. Fix the issues above before proceeding.")

    print("Validation passed.")
    return df