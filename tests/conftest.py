import pandas as pd
import pytest
from retail_ops.pipeline import classify, write_database


def source_frame(rows):
    d = pd.DataFrame(rows, columns=["invoice", "sku", "quantity", "timestamp", "price", "customer_id", "country"])
    d["description"] = "Test product"
    d["source_sheet"] = "Sheet 1"
    d["source_row"] = range(2, len(d) + 2)
    return d


@pytest.fixture
def source():
    return source_frame([
        ("1", "12345", 2, "2010-01-01", 10, 101, "UK"),
        ("2", "12345", 1, "2010-01-11", 10, 101, "UK"),
        ("3", "23456A", 2, "2010-04-15", 10, 202, "UK"),
        ("4", "23456A", 3, "2010-01-05", 10, None, "UK"),
        ("C5", "12345", -2, "2010-02-01", 10, 101, "UK"),
        ("C6", "55555", -1, "2010-02-01", 4, 101, "UK"),
        ("7", "POST", 1, "2010-01-01", 3, 101, "UK"),
        ("8", "12345", 1, "2010-01-01", 0, 101, "UK"),
        ("C9", "12345", 1, "2010-01-01", 10, 101, "UK"),
    ])


@pytest.fixture
def warehouse(source, tmp_path):
    path = tmp_path / "test.sqlite"
    write_database(classify(source), path)
    return path
