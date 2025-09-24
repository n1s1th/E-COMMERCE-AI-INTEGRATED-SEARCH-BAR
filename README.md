# E-commerce Search Bar MVP (Phase 1)

your_project/
├── app/
│   └── main.py                  # FastAPI entry point (API endpoints)
├── search/
│   ├── __init__.py              # Makes 'search' a Python module
│   ├── indexer.py               # Loads product JSON, builds Whoosh index
│   └── searcher.py              # Search, autocomplete, filtering logic
├── data/
│   └── products.json            # Your product dataset (example or real)
├── requirements.txt             # Python dependencies
├── README.md                    # Setup, usage, API doc

This implements a Whoosh-powered keyword search with autocomplete, fuzzy matching, and faceted filters via FastAPI.

## Features
- Keyword search across product_name, category, attributes, full_text
- Fuzzy/typo tolerance (`dreess` → `dress`)
- Facets: price range, size, color, brand, in-stock
- Relevance boosting: product_name > attributes > full_text
- Autocomplete/typeahead for product names, categories, brands
- Results with product card fields and simple highlighting

## Data format (example)
`data/products.json` should be a list or `{ "products": [...] }` where each product includes:

```json
{
  "id": "SKU-123",
  "product_name": "Iveena Dress",
  "brand_slug": "iveena",
  "category": "dresses",
  "product_type": "evening",
  "attributes": ["strapless", "silk"],
  "full_text": "An elegant strapless silk dress in emerald green.",
  "price": { "final_price": 129.99 },
  "variants": { "images": ["https://example.com/img/iveena.jpg"] },
  "sizes": ["S", "M", "L"],
  "color": "emerald",
  "in_stock": true,
  "pdp_url": "https://shop.example.com/p/iveena-dress"
}
```

## Setup

1) Install deps
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2) Prepare data
- Put your dataset at `data/products.json`

3) Build index
```
python -m search.indexer --data data/products.json --index indexdir
```

4) Run API
```
uvicorn app.main:app --reload --port 8000
```

5) Try it

- Search:
```
curl "http://localhost:8000/search?q=Iveena%20Dress"
curl "http://localhost:8000/search?q=dreess&fuzzy=true"
curl "http://localhost:8000/search?q=strapless&color=emerald&price_min=50&price_max=200&in_stock=true"
curl "http://localhost:8000/search?q=dress&brand=iveena&size=S,M"
```

- Autocomplete:
```
curl "http://localhost:8000/autocomplete?q=iv"
```

## Notes and tips
- Fuzzy matching: By default enabled with a max edit distance of 1 for tokens length >= 4.
- Facets: Pass multiple values as comma-separated lists (e.g., `size=S,M`).
- Highlighting: Simple highlights on `product_name` or `attributes`.
- Performance: Whoosh is great for MVPs and small-medium catalogs. For large-scale, migrate to OpenSearch/Elasticsearch with analyzers and aggregations.

## Next phases
- Add aggregations for facets (counts per brand/color/size)
- Synonyms (e.g., "tee" ↔ "t-shirt")
- Query understanding & re-ranking
- Switch to ES/OpenSearch keeping the same API shape