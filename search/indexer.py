import argparse
import json
import os
import shutil
import warnings
from typing import Any, Dict, Iterable

# Suppress harmless syntax warnings from Whoosh on Python 3.12+
warnings.filterwarnings("ignore", category=SyntaxWarning, module="whoosh")

from whoosh.analysis import StemmingAnalyzer, NgramWordAnalyzer
from whoosh.fields import Schema, ID, TEXT, KEYWORD, NUMERIC, BOOLEAN
from whoosh.index import create_in


def build_schema() -> Schema:
    return Schema(
        id=ID(stored=True, unique=True),
        product_name=TEXT(stored=True, analyzer=StemmingAnalyzer(), field_boost=3.0),
        brand_slug=KEYWORD(stored=True, lowercase=True, commas=True),
        category=KEYWORD(stored=True, lowercase=True, commas=True),
        product_type=KEYWORD(stored=True, lowercase=True, commas=True),
        attributes=TEXT(stored=True, analyzer=StemmingAnalyzer()),
        full_text=TEXT(stored=False, analyzer=StemmingAnalyzer()),
        price=NUMERIC(stored=True, sortable=True, numtype=int),
        sizes=KEYWORD(stored=True, lowercase=True, commas=True),
        color=KEYWORD(stored=True, lowercase=True, commas=True),
        in_stock=BOOLEAN(stored=True),
        pdp_url=ID(stored=True),
        image=ID(stored=True),
        autocomplete=TEXT(stored=True, analyzer=NgramWordAnalyzer(minsize=2, maxsize=15)),
    )


def flatten_attributes(attributes: Dict[str, Any]) -> str:
    tokens = []
    if not attributes:
        return ""
    for k, v in attributes.items():
        if isinstance(v, list):
            for item in v:
                tokens.append(f"{k}:{item}")
        elif isinstance(v, dict):
            for sub_k, sub_v in v.items():
                tokens.append(f"{k}_{sub_k}:{sub_v}")
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
        if isinstance(vals, list):
            attributes_text += " " + " ".join([f"{field}:{v}" for v in vals])
        elif isinstance(vals, str) and vals.strip():
            attributes_text += f" {field}:{vals.strip()}"

    variants = raw.get("variants") or []
    if not variants:
        # Fallback if product has no explicit variants
        variants = [{}]

    for idx, variant in enumerate(variants):
        variant_id = variant.get("variant_id") or str(idx)
        price_obj = variant.get("price") or {}
        raw_price = price_obj.get("final_price", raw.get("price", 0.0))
        try:
            price = int(round(float(raw_price)))
        except (TypeError, ValueError):
            price = 0

        raw_sizes = variant.get("sizes") or raw.get("sizes") or []
        if isinstance(raw_sizes, str):
            raw_sizes = [s.strip() for s in raw_sizes.split(",") if s.strip()]
        sizes_csv = ",".join([str(s).lower() for s in raw_sizes])

        raw_color = variant.get("color") or raw.get("color") or []
        if isinstance(raw_color, str):
            raw_color = [c.strip() for c in raw_color.split(",") if c.strip()]
        color_csv = ",".join([str(c).lower() for c in raw_color])

        in_stock = bool(variant.get("in_stock", raw.get("in_stock", True)))
        image = None
        images = variant.get("images") or raw.get("images") or []
        if isinstance(images, list) and images:
            image = images[0]
        elif isinstance(images, str):
            image = images

        pdp_url = variant.get("pdp_url") or raw.get("pdp_url") or ""

        # Enrich full_text and autocomplete sources
        category_clean = category.replace("-", " ").replace("_", " ")
        product_type_clean = product_type.replace("-", " ").replace("_", " ")
        brand_clean = brand_slug.replace("-", " ").replace("_", " ")
        variant_ft = variant.get("full_text") or ""

        full_text_components = [
            product_name,
            brand_slug,
            brand_clean,
            category,
            category_clean,
            product_type,
            product_type_clean,
            color_csv.replace(",", " "),
            sizes_csv.replace(",", " "),
            attributes_text,
            variant_ft,
        ]
        full_text = " ".join(dict.fromkeys(p for p in full_text_components if p)).strip()

        autocomplete_components = [
            product_name,
            brand_slug,
            brand_clean,
            category,
            category_clean,
            product_type,
            product_type_clean,
        ]
        autocomplete_source = " ".join(dict.fromkeys(p for p in autocomplete_components if p)).strip()

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
    # Safely recreate indexdir
    if os.path.exists(index_dir):
        shutil.rmtree(index_dir, ignore_errors=True)
    os.makedirs(index_dir, exist_ok=True)

    ix = create_in(index_dir, build_schema())
    writer = ix.writer()
    count = 0
    try:
        for doc in iter_products(json_path):
            writer.update_document(**doc)
            count += 1
        writer.commit()
        print(f"Indexed {count} product documents from {json_path} into {index_dir}")
    except Exception as e:
        writer.cancel()
        print(f"Indexing Error: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Whoosh index from products JSON")
    parser.add_argument("--data", "-d", required=True, help="Path to products.json")
    parser.add_argument("--index", "-i", default="indexdir", help="Index directory")
    args = parser.parse_args()
    build_index(args.data, args.index)
