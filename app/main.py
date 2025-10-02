from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from search.searcher import ProductSearch

app = FastAPI(title="E-commerce Search API", version="1.0")

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Or ["*"] for dev/testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --------------------------

search_engine = ProductSearch(index_dir="indexdir")

class ProductCard(BaseModel):
    id: str
    product_name: str
    price: float
    image: Optional[str]
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
    q: str,
    brand: Optional[str] = None,
    category: Optional[str] = None,
    color: Optional[str] = None,
    size: Optional[str] = None,
    in_stock: Optional[bool] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    page: int = 1,
    per_page: int = 20,
    fuzzy: bool = True,
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
    items = [ProductCard(**p) for p in products]
    return SearchResponse(total=total, page=page, per_page=per_page, items=items)

@app.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete(q: str):
    suggestions = search_engine.autocomplete(prefix=q, limit=10)
    return AutocompleteResponse(suggestions=suggestions)