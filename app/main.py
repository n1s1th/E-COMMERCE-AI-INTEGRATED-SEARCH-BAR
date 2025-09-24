from fastapi import FastAPI, Query
from typing import List, Optional
from pydantic import BaseModel
from search.searcher import ProductSearch
import os

INDEX_DIR = os.getenv("INDEX_DIR", "indexdir")
app = FastAPI(title="E-commerce Search API", version="0.1")

search_engine = ProductSearch(index_dir=INDEX_DIR)

class ProductCard(BaseModel):
    id: str
    product_name: str
    price: float
    thumbnail: Optional[str]
    sizes: List[str]
    color: Optional[str]
    brand_slug: Optional[str]
    category: Optional[str]
    in_stock: bool
    pdp_url: Optional[str]
    highlights: Optional[str] = None

class SearchResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[ProductCard]

class AutocompleteResponse(BaseModel):
    suggestions: List[str]

@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Search query"),
    brand: Optional[str] = Query(None, description="Comma-separated brand slugs"),
    category: Optional[str] = Query(None, description="Comma-separated categories"),
    color: Optional[str] = Query(None, description="Comma-separated colors"),
    size: Optional[str] = Query(None, description="Comma-separated sizes"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    price_min: Optional[float] = Query(None),
    price_max: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    fuzzy: bool = Query(True, description="Enable typo tolerance"),
):
    filters = {
        "brand": brand.split(",") if brand else None,
        "category": category.split(",") if category else None,
        "color": color.split(",") if color else None,
        "size": size.split(",") if size else None,
        "in_stock": in_stock,
        "price_min": price_min,
        "price_max": price_max,
    }
    total, products = search_engine.search(
        query=q,
        filters=filters,
        page=page,
        per_page=per_page,
        fuzzy=fuzzy,
    )
    items = [
        ProductCard(
            id=p["id"],
            product_name=p["product_name"],
            price=p["price"],
            thumbnail=p.get("image"),
            sizes=p.get("sizes", []),
            color=p.get("color"),
            brand_slug=p.get("brand_slug"),
            category=p.get("category"),
            in_stock=p.get("in_stock", False),
            pdp_url=p.get("pdp_url"),
            highlights=p.get("highlights"),
        )
        for p in products
    ]
    return SearchResponse(total=total, page=page, per_page=per_page, items=items)

@app.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete(q: str = Query(..., description="Partial term")):
    suggestions = search_engine.autocomplete(prefix=q, limit=10)
    return AutocompleteResponse(suggestions=suggestions)