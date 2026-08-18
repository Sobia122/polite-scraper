import pytest
from src.main import parse_price, BookSchema

def test_parse_price_normalization():
    assert parse_price("£51.77") == 51.77
    assert parse_price("Â£19.99") == 19.99

def test_valid_book_schema():
    data = {
        "title": "A Light in the Attic",
        "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "price_text": "£51.77",
        "price_gbp": 51.77,
        "availability_text": "In stock (22 available)",
        "rating_text": "Three",
        "rating_num": 3,
        "description": "A nice book",
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-08-18T00:00:00Z"
    }
    validated = BookSchema(**data)
    assert validated.price_gbp == 51.77
    assert validated.rating_num == 3

def test_invalid_price_schema():
    data = {
        "title": "Invalid Book",
        "product_url": "https://books.toscrape.com/catalogue/invalid",
        "price_text": "-10",
        "price_gbp": -10.0,  # Fails ge=0.0
        "availability_text": "In stock",
        "rating_text": "One",
        "rating_num": 1,
        "source_page": "https://books.toscrape.com/catalogue/page-1.html",
        "fetched_at": "2026-08-18T00:00:00Z"
    }
    with pytest.raises(Exception):
        BookSchema(**data)