from decimal import Decimal
import pytest

from app.core.errors import APIError
from app.core.validation import validate_decimal, Errors
from app.api.expenses import _expense_values, _income_values
from app.api.auth import _profile_field_errors


def test_validate_decimal_accepts_large_amounts():
    # 10 billion (11 digits before decimal)
    val = validate_decimal({"amount": "10000000000"}, "amount")
    assert val == Decimal("10000000000")

    # 100 billion (12 digits before decimal, user's input)
    val = validate_decimal({"amount": "100000000000"}, "amount")
    assert val == Decimal("100000000000")

    # Max supported (14 digits before decimal, 2 after)
    val = validate_decimal({"amount": "99999999999999.99"}, "amount")
    assert val == Decimal("99999999999999.99")


def test_validate_decimal_rejects_overflow():
    # 15 digits before decimal
    with pytest.raises(APIError) as exc_info:
        validate_decimal({"amount": "100000000000000"}, "amount")
    err = exc_info.value.body
    assert "amount" in err
    assert "Ensure that there are no more than 14 digits before the decimal point." in err["amount"][0]


def test_validate_decimal_rejects_excessive_decimals():
    with pytest.raises(APIError) as exc_info:
        validate_decimal({"amount": "10.123"}, "amount")
    err = exc_info.value.body
    assert "Ensure that there are no more than 2 decimal places." in err["amount"][0]


def test_validate_decimal_min_value():
    with pytest.raises(APIError) as exc_info:
        validate_decimal({"amount": "0.00"}, "amount", min_value=Decimal("0.01"))
    err = exc_info.value.body
    assert "Ensure this value is greater than or equal to 0.01." in err["amount"][0]


def test_expense_and_income_values_support_large_amounts():
    # Valid large income
    errors, values = _income_values(
        {
            "amount": "100000000000",
            "title": "Hooray",
            "source_type": "scholarship",
            "date": "2026-11-20",
        },
        partial=False,
    )
    assert not bool(errors)
    assert values["amount"] == Decimal("100000000000")

    # Overflow income
    errors, values = _income_values(
        {
            "amount": "100000000000000",
            "title": "Hooray",
            "source_type": "scholarship",
            "date": "2026-11-20",
        },
        partial=False,
    )
    assert bool(errors)
    assert "amount" in errors.errors
    assert (
        "Ensure that there are no more than 14 digits before the decimal point."
        in errors.errors["amount"][0]
    )


def test_profile_monthly_income_validation():
    # Valid 100 billion
    errs = _profile_field_errors({"monthly_income": "100000000000"})
    assert "monthly_income" not in errs

    # Overflow
    errs_overflow = _profile_field_errors({"monthly_income": "100000000000000"})
    assert "monthly_income" in errs_overflow
    assert (
        "Ensure that there are no more than 14 digits before the decimal point."
        in errs_overflow["monthly_income"][0]
    )
