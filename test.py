"""
Comprehensive test script for E-Commerce Search API and Engine.
Run with: python test.py
"""
import sys
from fastapi.testclient import TestClient
from app.main import app
from search.searcher import ProductSearch

def run_tests():
    print("=" * 60)
    print("Running E-Commerce AI Search Engine Verification Tests")
    print("=" * 60)

    # 1. Test Search Engine Direct
    print("\n[1/3] Testing ProductSearch engine...")
    ps = ProductSearch(index_dir="indexdir", data_path="data/products.json")

    # Empty query should return all items
    total, items = ps.search("")
    assert total > 0, "Empty search should return catalog items"
    print(f"  [OK] Empty search returned {total} products")

    # Fuzzy search
    total, items = ps.search("maxy", fuzzy=True)
    assert total > 0 and "Maxi" in items[0]["product_name"], "Fuzzy search should find Maxi dresses"
    print(f"  [OK] Typo-tolerant search for 'maxy' matched: {items[0]['product_name']}")

    # Brand search
    total, items = ps.search("bayleee")
    assert total > 0, "Brand query should match products"
    print(f"  [OK] Brand search for 'bayleee' returned {total} products")

    # Autocomplete
    suggestions = ps.autocomplete("dr", limit=5)
    assert len(suggestions) > 0, "Autocomplete should return suggestions"
    print(f"  [OK] Autocomplete for 'dr' returned: {suggestions[:3]}...")

    # 2. Test FastAPI Endpoints via TestClient
    print("\n[2/3] Testing FastAPI HTTP endpoints...")
    client = TestClient(app)

    # Root & Health
    r = client.get("/")
    assert r.status_code == 200 and r.json().get("status") == "healthy"
    print("  [OK] GET / returns healthy status")

    # Search endpoint
    r = client.get("/search?q=dress&price_min=5000&price_max=8500")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    print(f"  [OK] GET /search with price filter returned {data['total']} items")

    # Autocomplete endpoint
    r = client.get("/autocomplete?q=max&limit=4")
    assert r.status_code == 200
    suggestions = r.json().get("suggestions", [])
    assert len(suggestions) > 0
    print(f"  [OK] GET /autocomplete returned {len(suggestions)} suggestions: {suggestions}")

    # 3. Test Edge Cases
    print("\n[3/3] Testing edge cases (malformed input, special characters)...")
    for bad_q in ["", "   ", ":::", "&&", "(unclosed", chr(34) + "quote", "NOT AND", "*"]:
        r = client.get(f"/search?q={bad_q}")
        assert r.status_code == 200, f"Query '{bad_q}' failed with {r.status_code}"
    print("  [OK] All special character queries handled safely without 500 errors")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! Backend is fully functional.")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
