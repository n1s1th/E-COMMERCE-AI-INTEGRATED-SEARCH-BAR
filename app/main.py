from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, List, Optional
from pydantic import BaseModel, Field
from search.searcher import ProductSearch

app = FastAPI(
    title="E-commerce Search API",
    description="High-performance search API with fuzzy matching, autocomplete, and filters.",
    version="1.0.0",
)

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
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
    image: Optional[str] = None
    sizes: List[str] = Field(default_factory=list)
    color: Optional[str] = None
    brand_slug: Optional[str] = None
    category: Optional[str] = None
    product_type: Optional[str] = None
    in_stock: bool = True
    pdp_url: Optional[str] = None
    highlights: Optional[str] = None


class SearchResponse(BaseModel):
    total: int
    page: int
    per_page: int
    items: List[ProductCard]


class AutocompleteResponse(BaseModel):
    suggestions: List[str]


@app.get("/")
def root():
    return {
        "name": "E-commerce Search API",
        "status": "healthy",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


def _clean_csv(param: Any) -> Optional[List[str]]:
    if isinstance(param, str):
        items = [item.strip() for item in param.split(",") if item.strip()]
        return items if items else None
    return None


@app.get("/search", response_model=SearchResponse)
def search(
    q: str = Query("", description="Search query string"),
    brand: Optional[str] = Query(default=None, description="Comma-separated brand slugs"),
    category: Optional[str] = Query(default=None, description="Comma-separated categories"),
    product_type: Optional[str] = Query(default=None, description="Comma-separated product types"),
    color: Optional[str] = Query(default=None, description="Comma-separated colors"),
    size: Optional[str] = Query(default=None, description="Comma-separated sizes"),
    in_stock: Optional[bool] = Query(default=None, description="Filter by stock availability"),
    price_min: Optional[float] = Query(default=None, description="Minimum price filter"),
    price_max: Optional[float] = Query(default=None, description="Maximum price filter"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(default=20, ge=1, le=100, description="Number of items per page"),
    fuzzy: bool = Query(default=True, description="Enable typo-tolerant fuzzy matching"),
):
    q_str = q if isinstance(q, str) else ""
    page_num = int(page) if isinstance(page, (int, float, str)) and not isinstance(page, bool) else 1
    per_page_num = int(per_page) if isinstance(per_page, (int, float, str)) and not isinstance(per_page, bool) else 20
    is_fuzzy = bool(fuzzy) if isinstance(fuzzy, (bool, int, str)) else True
    min_price = float(price_min) if isinstance(price_min, (int, float, str)) else None
    max_price = float(price_max) if isinstance(price_max, (int, float, str)) else None
    stock_val = bool(in_stock) if isinstance(in_stock, (bool, int, str)) else None

    filters = {
        "brand": _clean_csv(brand),
        "category": _clean_csv(category),
        "product_type": _clean_csv(product_type),
        "color": _clean_csv(color),
        "size": _clean_csv(size),
        "in_stock": stock_val,
        "price_min": min_price,
        "price_max": max_price,
    }

    total, products = search_engine.search(
        query=q_str,
        filters=filters,
        page=page_num,
        per_page=per_page_num,
        fuzzy=is_fuzzy,
    )
    items = [ProductCard(**p) for p in products]
    return SearchResponse(total=total, page=page_num, per_page=per_page_num, items=items)


@app.get("/autocomplete", response_model=AutocompleteResponse)
def autocomplete(
    q: str = Query("", description="Prefix or keyword for suggestions"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum suggestions to return"),
):
    q_str = q if isinstance(q, str) else ""
    limit_num = int(limit) if isinstance(limit, (int, float, str)) and not isinstance(limit, bool) else 10
    suggestions = search_engine.autocomplete(prefix=q_str, limit=limit_num)
    return AutocompleteResponse(suggestions=suggestions)
