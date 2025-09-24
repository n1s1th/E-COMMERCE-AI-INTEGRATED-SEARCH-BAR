import json
import os
from typing import Any, Dict, Iterable
from whoosh import index
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC, BOOLEAN
from whoosh.analysis import StemmingAnalyzer, NgramWordAnalyzer
from whoosh.index import create_in
from whoosh.writing import AsyncWriter

def build_schema() -> Schema:
    return Schema(
        id=ID(stored=True, unique=True),
        product_name=TEXT(stored=True, analyzer=StemmingAnalyzer(), field_boost=3.0),
        brand_slug=KEYWORD(stored=True, lowercase=True, commas=True),
        category=KEYWORD(stored=True, lowercase=True, commas=True),
        product_type=KEYWORD(stored=True, lowercase=True, commas=True),
        attributes=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        full_text=TEXT(stored=False, analyzer=StemmingAnalyzer()),
        price=NUMERIC(stored=True, sortable=True, numtype=float),
        sizes=KEYWORD(stored=True, lowercase=True, commas=True),
        color=KEYWORD(stored=True, lowercase=True, commas=True),
        in_stock=BOOLEAN(stored=True),
        pdp_url=ID(stored=True),
        image=ID(stored=True),
        # For typeahead: word-level ngrams for prefix matches
        autocomplete=TEXT(stored=False, analyzer=NgramWordAnalyzer(minsize=2, maxsize=15)),
    )

def flatten_record(raw: Dict[str, Any]) -> Dict[str, Any]:
    product_name = (raw.get("product_name") or "").strip()
    brand_slug = (raw.get("brand_slug") or "").strip().lower()
    category = (raw.get("category") or "").strip().lower()
    product_type = (raw.get("product_type") or "").strip().lower()

    # attributes could be list[str] or dict; assume list[str] for MVP
    attributes_list = raw.get("attributes") or []
    if isinstance(attributes_list, dict):
        attributes_list = [f"{k}:{v}" for k, v in attributes_list.items()]
    attributes_text = " ".join([str(a) for a in attributes_list])

    sizes_list = raw.get("sizes") or []
    sizes_csv = ",".join([str(s).lower() for s in sizes_list])

    color = (raw.get("color") or "").strip().lower()
    in_stock = bool(raw.get("in_stock", False))

    price_obj = raw.get("price") or {}
    price = float(price_obj.get("final_price", 0.0))

    # thumbnail
    image = None
    variants = raw.get("variants") or {}
    images = variants.get("images") or []
    if isinstance(images, list) and images:
        image = images[0]

    pdp_url = raw.get("pdp_url") or raw.get("url") or ""

    full_text = raw.get("full_text") or raw.get("description") or ""

    # id heuristic
    pid = str(raw.get("id") or raw.get("sku") or raw.get("slug") or f"{product_name}-{brand_slug}-{category}-{price}")

    autocomplete_source = " ".join(
        [product_name, brand_slug, category]
    ).strip()

    return dict(
        id=pid,
        product_name=product_name,
        brand_slug=brand_slug,
        category=category,
        product_type=product_type,
        attributes=attributes_text,
        full_text=full_text,
        price=price,
        sizes=sizes_csv,
        color=color,
        in_stock=in_stock,
        pdp_url=pdp_url,
        image=image or "",
        autocomplete=autocomplete_source,
    )

def iter_products(json_path: str) -> Iterable[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # support either {"products":[...]} or a list
    items = data.get("products") if isinstance(data, dict) else data
    for raw in items:
        yield flatten_record(raw)

def build_index(json_path: str, index_dir: str = "indexdir") -> None:
    os.makedirs(index_dir, exist_ok=True)
    if not os.listdir(index_dir):
        ix = create_in(index_dir, build_schema())
    else:
        ix = index.open_dir(index_dir)
    writer = AsyncWriter(ix)
    try:
        for doc in iter_products(json_path):
            writer.update_document(**doc)
        writer.commit()
        print(f"Indexed products from {json_path} into {index_dir}")
    except Exception:
        writer.cancel()
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build Whoosh index from products JSON")
    parser.add_argument("--data", "-d", required=True, help="Path to products.json")
    parser.add_argument("--index", "-i", default="indexdir", help="Index directory")
    args = parser.parse_args()
    build_index(args.data, args.index)