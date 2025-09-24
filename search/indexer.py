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
        autocomplete=TEXT(stored=False, analyzer=NgramWordAnalyzer(minsize=2, maxsize=15)),
    )

def flatten_attributes(attributes: Dict[str, Any]) -> str:
    if not attributes:
        return ""
    tokens = []
    for k, v in attributes.items():
        if isinstance(v, list):
            for item in v:
                tokens.append(f"{k}:{item}")
        else:
            tokens.append(f"{k}:{v}")
    return " ".join(tokens)

def flatten_record(raw: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    product_id = str(raw.get("product_id") or raw.get("id") or "")
    product_name = (raw.get("product_name") or "").strip()
    brand_slug = (raw.get("brand_slug") or "").strip().lower()
    category = (raw.get("category") or "").strip().lower()
    product_type = (raw.get("product_type") or "").strip().lower()

    attributes_text = flatten_attributes(raw.get("attributes", {}))
    for field in ["gender", "occasion", "style"]:
        vals = raw.get(field)
        if vals:
            attributes_text += " " + " ".join([f"{field}:{v}" for v in vals])

    variants = raw.get("variants") or []
    for variant in variants:
        variant_id = variant.get("variant_id") or ""
        price_obj = variant.get("price") or {}
        raw_price = price_obj.get("final_price", 0.0)
        try:
            price = float(raw_price) if raw_price is not None else 0.0
        except (TypeError, ValueError):
            price = 0.0

        sizes_list = variant.get("sizes") or []
        sizes_csv = ",".join([str(s).lower() for s in sizes_list])
        color_list = variant.get("color") or []
        color_csv = ",".join([str(c).lower() for c in color_list])
        in_stock = bool(variant.get("in_stock", False))
        image = None
        images = variant.get("images") or []
        if isinstance(images, list) and images:
            image = images[0]
        pdp_url = variant.get("pdp_url") or ""
        full_text = variant.get("full_text") or ""
        autocomplete_source = " ".join([product_name, brand_slug, category]).strip()
        
        yield dict(
            id=f"{product_id}-{variant_id}",
            product_name=product_name,
            brand_slug=brand_slug,
            category=category,
            product_type=product_type,
            attributes=attributes_text,
            full_text=full_text,
            price=price,
            sizes=sizes_csv,
            color=color_csv,
            in_stock=in_stock,
            pdp_url=pdp_url,
            image=image or "",
            autocomplete=autocomplete_source,
    )
        
def iter_products(json_path: str) -> Iterable[Dict[str, Any]]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = data.get("products") if isinstance(data, dict) else data
    for raw in items:
        yield from flatten_record(raw)

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