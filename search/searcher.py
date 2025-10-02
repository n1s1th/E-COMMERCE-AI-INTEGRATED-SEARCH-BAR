import os
import re
from typing import Dict, List, Optional, Tuple, Any
from whoosh import index
from whoosh.qparser import MultifieldParser, OrGroup, FuzzyTermPlugin, WildcardPlugin
from whoosh.query import And, Or, Term, NumericRange, Prefix
from whoosh.scoring import BM25F

DEFAULT_FIELDS = ["product_name", "category", "attributes", "full_text"]

class ProductSearch:
    def __init__(self, index_dir: str = "indexdir"):
        if not os.path.exists(index_dir) or not os.listdir(index_dir):
            raise RuntimeError(f"Index not found in {index_dir}. Build it with: python -m search.indexer --data data/products.json")
        self.ix = index.open_dir(index_dir)
        self.weighting = BM25F(
            field_B={'product_name': 1.0, 'attributes': 1.0, 'full_text': 1.0},
            K1=1.5,
            B=0.75
        )

    def _build_parser(self):
        parser = MultifieldParser(DEFAULT_FIELDS, schema=self.ix.schema, group=OrGroup.factory(0.9))
        parser.add_plugin(FuzzyTermPlugin())
        parser.add_plugin(WildcardPlugin())
        return parser

    def _apply_fuzzy(self, q: str, maxdist: int = 1) -> str:
        tokens = re.findall(r"[A-Za-z0-9]+", q)
        fuzzed = []
        for t in tokens:
            if len(t) >= 4:
                fuzzed.append(f"{t}~{maxdist}")
            else:
                fuzzed.append(t)
        return " ".join(fuzzed) if fuzzed else q

    def _build_filter(self, filters: Dict[str, Any]):
        terms = []
        if filters.get("brand"):
            terms.append(Or([Term("brand_slug", b.lower()) for b in filters["brand"] if b]))
        if filters.get("category"):
            terms.append(Or([Term("category", c.lower()) for c in filters["category"] if c]))
        if filters.get("color"):
            terms.append(Or([Term("color", col.lower()) for col in filters["color"] if col]))
        if filters.get("size"):
            terms.append(Or([Term("sizes", s.lower()) for s in filters["size"] if s]))
        if filters.get("in_stock") is not None:
            terms.append(Term("in_stock", bool(filters["in_stock"])))
        price_min = filters.get("price_min")
        price_max = filters.get("price_max")
        if price_min is not None or price_max is not None:
            lo = float(price_min) if price_min is not None else None
            hi = float(price_max) if price_max is not None else None
            terms.append(NumericRange("price", lo=lo, hi=hi, startexcl=False, endexcl=False))
        if not terms:
            return None
        return And(terms) if len(terms) > 1 else terms[0]

    def search(self, query: str, filters: Dict[str, Any], page: int = 1, per_page: int = 20, fuzzy: bool = True) -> Tuple[int, List[Dict[str, Any]]]:
        qp = self._build_parser()
        qstring = self._apply_fuzzy(query, maxdist=1) if fuzzy else query
        q = qp.parse(qstring)
        filter_q = self._build_filter(filters or {})
        offset = (page - 1) * per_page
        with self.ix.searcher(weighting=self.weighting) as s:
            results = s.search(q, limit=offset + per_page, filter=filter_q)
            total = len(results)
            hits = results[offset: offset + per_page]
            items: List[Dict[str, Any]] = []
            for hit in hits:
                hl = hit.highlights("product_name") or hit.highlights("attributes")
                items.append({
                    "id": hit["id"],
                    "product_name": hit["product_name"],
                    "price": hit.get("price", 0.0),
                    "image": hit.get("image"),
                    "sizes": (hit.get("sizes") or "").split(",") if hit.get("sizes") else [],
                    "color": hit.get("color"),
                    "brand_slug": hit.get("brand_slug"),
                    "category": hit.get("category"),
                    "in_stock": hit.get("in_stock", False),
                    "pdp_url": hit.get("pdp_url"),
                    "highlights": hl or None,
                })
            return total, items

    def autocomplete(self, prefix: str, limit: int = 10) -> List[str]:
        if not prefix:
            return []
        with self.ix.searcher() as s:
            q = Prefix("autocomplete", prefix.lower())
            results = s.search(q, limit=limit)
            suggestions = []
            seen = set()
            for hit in results:
                for cand in (hit.get("product_name"), hit.get("category"), hit.get("brand_slug")):
                    if cand and cand.lower().startswith(prefix.lower()):
                        key = cand.lower()
                        if key not in seen:
                            seen.add(key)
                            suggestions.append(cand)
                if len(suggestions) >= limit:
                    break
            return suggestions[:limit]