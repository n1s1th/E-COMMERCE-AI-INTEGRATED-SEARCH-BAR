import os
import re
import warnings
from typing import Dict, List, Optional, Tuple, Any

# Suppress harmless syntax warnings from Whoosh on Python 3.12+
warnings.filterwarnings("ignore", category=SyntaxWarning, module="whoosh")

from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup, FuzzyTermPlugin, WildcardPlugin
from whoosh.query import And, Or, Term, NumericRange, Prefix, Wildcard, Every
from whoosh.scoring import BM25F

DEFAULT_FIELDS = [
    "product_name",
    "category",
    "brand_slug",
    "product_type",
    "color",
    "attributes",
    "full_text",
]

DEFAULT_FIELDBOOSTS = {
    "product_name": 3.0,
    "brand_slug": 2.0,
    "category": 2.0,
    "product_type": 1.5,
    "color": 1.5,
    "attributes": 1.0,
    "full_text": 1.0,
}


class ProductSearch:
    def __init__(self, index_dir: str = "indexdir", data_path: str = "data/products.json"):
        self.index_dir = index_dir
        if not os.path.exists(index_dir) or not os.listdir(index_dir):
            if os.path.exists(data_path):
                from search.indexer import build_index
                print(f"Index not found in '{index_dir}'. Auto-building index from '{data_path}'...")
                build_index(data_path, index_dir)
            else:
                raise RuntimeError(
                    f"Index not found in '{index_dir}' and data file '{data_path}' does not exist. "
                    "Build it with: python -m search.indexer --data data/products.json"
                )
        self.ix = index.open_dir(index_dir)
        self.weighting = BM25F(
            B=0.75,
            K1=1.5,
            product_name_B=1.0,
            attributes_B=1.0,
            full_text_B=1.0,
        )

    def _build_parser(self):
        parser = MultifieldParser(
            DEFAULT_FIELDS,
            schema=self.ix.schema,
            fieldboosts=DEFAULT_FIELDBOOSTS,
            group=OrGroup.factory(0.9),
        )
        parser.add_plugin(FuzzyTermPlugin())
        parser.add_plugin(WildcardPlugin())
        return parser

    def _apply_fuzzy(self, q: str, maxdist: int = 1) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", q)
        if not tokens:
            return q
        fuzzed = []
        for t in tokens:
            if len(t) >= 4:
                # Prioritize exact term over fuzzy match
                fuzzed.append(f"({t}^3.0 OR {t}~{maxdist})")
            else:
                fuzzed.append(t)
        return " ".join(fuzzed)

    def _build_filter(self, filters: Dict[str, Any]):
        terms = []
        if filters.get("brand"):
            brands = [b.lower() for b in filters["brand"] if b]
            if brands:
                terms.append(Or([Term("brand_slug", b) for b in brands]))

        if filters.get("category"):
            cats = [c.lower() for c in filters["category"] if c]
            if cats:
                terms.append(Or([Term("category", c) for c in cats]))

        if filters.get("product_type"):
            types = [pt.lower() for pt in filters["product_type"] if pt]
            if types:
                terms.append(Or([Term("product_type", pt) for pt in types]))

        if filters.get("color"):
            colors = [col.lower() for col in filters["color"] if col]
            if colors:
                terms.append(Or([Term("color", col) for col in colors]))

        if filters.get("size"):
            sizes = [s.lower() for s in filters["size"] if s]
            if sizes:
                terms.append(Or([Term("sizes", s) for s in sizes]))

        if filters.get("in_stock") is not None:
            terms.append(Term("in_stock", bool(filters["in_stock"])))

        price_min = filters.get("price_min")
        price_max = filters.get("price_max")
        if price_min is not None or price_max is not None:
            lo = int(float(price_min)) if price_min is not None else None
            hi = int(float(price_max)) if price_max is not None else None
            terms.append(NumericRange("price", start=lo, end=hi, startexcl=False, endexcl=False))

        if not terms:
            return None
        return And(terms) if len(terms) > 1 else terms[0]

    def search(
        self,
        query: str = "",
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20,
        fuzzy: bool = True,
    ) -> Tuple[int, List[Dict[str, Any]]]:
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), 100))
        offset = (page - 1) * per_page

        filter_q = self._build_filter(filters or {})

        q_clean = (query or "").strip()
        if not q_clean:
            q = Every()
        else:
            qp = self._build_parser()
            qstring = self._apply_fuzzy(q_clean, maxdist=1) if fuzzy else q_clean
            try:
                q = qp.parse(qstring)
            except Exception:
                # Fallback to standard query without fuzzy plugins if parsing failed
                try:
                    q = qp.parse(q_clean)
                except Exception:
                    q = Every()

        with self.ix.searcher(weighting=self.weighting) as s:
            results = s.search(q, limit=offset + per_page, filter=filter_q, terms=True)
            total = len(results)
            hits = results[offset : offset + per_page]
            items: List[Dict[str, Any]] = []

            for hit in hits:
                hl = None
                try:
                    hl = (
                        hit.highlights("product_name")
                        or hit.highlights("attributes")
                        or hit.highlights("category")
                        or hit.highlights("brand_slug")
                        or None
                    )
                except Exception:
                    hl = None

                raw_sizes = hit.get("sizes") or ""
                sizes = [sz.strip() for sz in raw_sizes.split(",") if sz.strip()]

                items.append({
                    "id": hit["id"],
                    "product_name": hit["product_name"],
                    "price": float(hit.get("price", 0.0)),
                    "image": hit.get("image") or None,
                    "sizes": sizes,
                    "color": hit.get("color") or None,
                    "brand_slug": hit.get("brand_slug") or None,
                    "category": hit.get("category") or None,
                    "product_type": hit.get("product_type") or None,
                    "in_stock": hit.get("in_stock", True),
                    "pdp_url": hit.get("pdp_url") or None,
                    "highlights": hl,
                })

            return total, items

    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        if not prefix or not prefix.strip():
            return []

        p = prefix.strip().lower()
        limit = max(1, min(int(limit), 50))

        with self.ix.searcher() as s:
            q = Or([
                Prefix("autocomplete", p),
                Prefix("product_name", p),
                Prefix("category", p),
                Prefix("brand_slug", p),
                Prefix("product_type", p),
                Wildcard("product_name", f"*{p}*"),
                Wildcard("category", f"*{p}*"),
                Wildcard("brand_slug", f"*{p}*"),
            ])
            results = s.search(q, limit=max(50, limit * 5))

            p1: List[str] = []  # Exact prefix match on candidate string
            p2: List[str] = []  # Any word inside starts with prefix
            p3: List[str] = []  # Substring match anywhere
            seen = set()

            for hit in results:
                candidates = [
                    hit.get("product_name"),
                    hit.get("category"),
                    hit.get("product_type"),
                    hit.get("brand_slug"),
                ]
                for cand in candidates:
                    if not cand:
                        continue
                    cand_str = str(cand).strip()
                    cand_lower = cand_str.lower()
                    if cand_lower in seen:
                        continue

                    words = cand_lower.split()
                    if cand_lower.startswith(p):
                        seen.add(cand_lower)
                        p1.append(cand_str)
                    elif any(w.startswith(p) for w in words):
                        seen.add(cand_lower)
                        p2.append(cand_str)
                    elif p in cand_lower:
                        seen.add(cand_lower)
                        p3.append(cand_str)

            suggestions = (p1 + p2 + p3)[:limit]
            return suggestions
