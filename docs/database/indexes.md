# Nexa Mall Database Index Strategy

> Every index must be able to finish this sentence:
> **"This index was built for query #X."**
> If it cannot, it does not get created. Indexes speed reads but
> tax every INSERT/UPDATE/DELETE with storage and maintenance.

Method (enforced in this project):

```text
Query Pattern → WHERE + ORDER BY + JOIN → Index Design
→ EXPLAIN → Migration → Re-measure
```

Audit tool: `python manage.py audit_indexes` prints the REAL
indexes/constraints of every table next to what each model declares
(`Meta.indexes`), making model-vs-database drift visible before any
migration.

---

## Index Strategy Matrix

| Domain | Query (WHERE / ORDER BY) | Index | Reason |
|---|---|---|---|
| Product | `shop + status` | `(shop, status)` | Management listing scope |
| Product | `status` + `ORDER BY -created_at, id` | `(status, created_at)` | Public listing (filter + ordering prefix) |
| Product | `id = UUID` | PRIMARY KEY | Detail lookup — no manual `id` index (PK already is one) |
| Product | `shop + slug` | UNIQUE `(shop, slug)` | Slug uniqueness — unique constraint implies the index, no duplicate index |
| Variant | `product + status` | `(product, status)` | Variant lookup per product |
| Variant | `sku` | UNIQUE `sku` | Global SKU identity |
| Product (search) | `UPPER(name/slug/description) LIKE '%q%'` | GIN `Upper(col)` + `gin_trgm_ops` (pg_trgm) | Substring search: leading-wildcard LIKE cannot use B-tree; trigram bitmap scan |
| Variant (search) | `UPPER(sku/name) LIKE '%q%'` | GIN `Upper(col)` + `gin_trgm_ops` | Search on variants__sku / variants__name |
| Brand (search) | `UPPER(name) LIKE '%q%'` | GIN `Upper(name)` + `gin_trgm_ops` | Search on brand__name |
| InventoryItem | `variant` (OneToOne) | UNIQUE `variant` | `get(variant=...)` runtime lookup |
| Reservation | `status + expires_at` | `(status, expires_at)` | Expiration worker sweep |
| Reservation | `inventory + status` | `(inventory, status)` | Active reservations per item |
| Reservation | `order + status` | `(order, status)` | Reservations per order |
| Order | `user + ORDER BY -created_at, id` | `(user, -created_at, id)` `order_user_created_id_idx` | Customer order listing (ADR-001) |
| Order | `shop + ORDER BY -created_at, id` | `(shop, -created_at, id)` `order_shop_created_id_idx` | Shop management listing (ADR-001) |
| Order | `shop + status` / `(status, created_at)` | kept from earlier phases | Scoped/status sweeps |
| OrderItem | `order` / `variant` | automatic FK indexes | Django indexes FKs by default |
| StockMovement | `inventory` | automatic FK index | History per item — no manual duplicate |
| TenantMembership | `user + tenant` | UNIQUE `(user, tenant)` | Join path user → tenant; also serves `filter(tenant, user)` |
| Cart | `user + shop` | UNIQUE `(user, shop)` (+ partial ACTIVE) | One active cart per user-shop |

## EXPLAIN evidence (SQLite dev, small seeds)

```text
Public product list   → INDEX SCAN on (status, created_at)
Shop-only filter      → INDEX SCAN on (shop, status)      [leftmost prefix]
Status-only filter    → INDEX SCAN on (status, created_at) [leftmost prefix]
Customer orders       → INDEX SCAN on order_user_created_id_idx, NO sort node (v2)
Shop management       → INDEX SCAN on order_shop_created_id_idx, NO sort node (v2)
shop_orders selector  → PK on shop, UNIQUE (user_id, tenant_id) on membership,
                        then the (shop, -created_at, id) index on orders
```

No sequential scans on the measured workloads. Planner may still
choose a seq scan in tiny tables — that is a cost decision, not an
index defect.

---

## ADR-001 — Order Listing Indexes

**Decision (v2, refined):** `(user, -created_at, id)` and
`(shop, -created_at, id)` on `orders.Order`, named
`order_user_created_id_idx` / `order_shop_created_id_idx`
(migration `orders.0003`).

**Reason:** the two dominant listing workloads are
`WHERE user = X ORDER BY created_at DESC, id` (customer history) and
`WHERE shop = X ORDER BY created_at DESC, id` (shop management).
Matching the EXACT shape — leading equality column, the sort column
in the query's direction, then the deterministic `id` tie-breaker —
lets the B-tree serve the filter AND the whole ordering. EXPLAIN
before/after (SQLite dev): the two-column version needed
`USE TEMP B-TREE FOR RIGHT PART OF ORDER BY` (a separate sort); the
three-column version is a single index search with no sort node.

**Evolution (v1 → v2):** v1 was `(user, created_at)` /
`(shop, created_at)` — correct for the filter+sort prefix, but the
real query also sorts by `id` as a pagination tie-breaker. The v2
indexes REPLACE the v1 ones in the same migration (removed
`orders_orde_user_id_37fed6_idx`, `orders_orde_shop_id_c267ca_idx`);
keeping both would tax every order INSERT twice for one workload.
This is index design as a living decision: query understood more
precisely → index refined — never a blind first draft.

**Rejected:**
- Single-column `(user)` / `(shop)` / `(created_at)` indexes — two
  separate structures cannot serve filter+ORDER BY the way one
  composite can; `(created_at)` alone has terrible selectivity.
- Composite `(id, user)` for order detail — `id` is the PK; a PK
  lookup already narrows to one row, appending `user` adds nothing.
- Keeping the v1 two-column indexes alongside v2 — duplicate
  maintenance cost for the same workload.

---

## ADR-002 — Trigram GIN Search Indexes (pg_trgm)

**Decision:** PostgreSQL (docker service `postgres`) as the project
database; hand-written migration `catalog.0003` enables the
`pg_trgm` extension BEFORE `catalog.0004/0005` create six GIN
trigram indexes — as **functional indexes on `Upper(col)`** with
`OpClass(..., gin_trgm_ops)`: `product_name/slug/desc`,
`variant_sku/name`, `brand_name`.

**Reason:** DRF `SearchFilter`/`icontains` compiles to
`UPPER(col) LIKE '%q%'` — NOT `ILIKE` (verified from the generated
SQL). Two consequences:
1. a plain B-tree cannot serve a leading-wildcard LIKE at all;
2. a plain-column GIN would still never match, because the
   predicate is `UPPER(col)` — the index must be on the EXPRESSION
   (`Upper(col)`), making the index and the predicate identical.
`pg_trgm` turns the trigrams of the pattern into a bitmap index
scan of candidate rows.

**EXPLAIN ANALYZE evidence** (60k-row seed, `ANALYZE` run):
- needle search (1/60000): **Bitmap Heap Scan + Bitmap Index Scan
  on product_name_trgm_idx**, `Index Cond: (upper((name)::text) ~~
  '%MODEL 00427%')`, 6.1ms
- broad search (12.5% selectivity): planner rightly stays on a
  Seq Scan — index usage is a cost decision; a small table or a
  low-selectivity pattern does not need (and may not use) the
  index. That is not a defect.

**Rejected / deferred:**
- Plain-column GIN (first attempt) — never usable: the query
  predicate is UPPER(col), verified by EXPLAIN before the fix
- Elasticsearch/OpenSearch — deferred until search needs fuzzy
  ranking, typo tolerance, synonyms, faceting or hundreds of
  millions of docs; do not introduce a distributed search engine
  before the workload demands it
- All-search-fields GIN everywhere — each GIN adds write cost;
  the description index especially is a workload-driven decision
  to revisit with real data

**Operational notes:** migrations use plain `AddIndex` (dev);
for large production tables use `AddIndexConcurrently`. Refresh
statistics with `ANALYZE` after bulk loads.

---

## Deliberately NOT built (yet) — and why

| Candidate | Why deferred |
|---|---|
| `Index(fields=["id"])` anywhere | PK is already the index |
| `Index(fields=["shop", "slug"])` on Product | the UNIQUE constraint already creates it |
| `Index(fields=["inventory"])` on StockMovement | automatic FK index already exists |
| `(status, shop)` on Product | dominant queries lead with shop; leftmost-prefix rule |
| `(status, created_at)` NEW variants like `(-created_at, id)` | B-tree reverse scan already serves DESC; no duplicate |
| Partial index `(created_at) WHERE status=ACTIVE` | needs real data distribution first (selectivity) |
| Covering index / INCLUDE | needs index-only-scan workload evidence |
| pg_trgm / GIN for search fields | built (ADR-002) — see above; Elasticsearch deferred |

Rules captured here:

1. **PK / Unique constraint / FK** → already indexed by the
   database or Django; never duplicate them.
2. **Leftmost prefix** — a composite serves filters on its leading
   columns; design order by the dominant query's equality columns
   first, ordering column last.
3. **Selectivity** — an index on a 95%-value column (e.g. status
   when almost everything is ACTIVE) buys little; UUID/PK lookups
   are the high-selectivity sweet spot.
4. **cost ≠ time** — EXPLAIN's cost unit is an internal planner
   estimate, not milliseconds; real timing requires EXPLAIN
   ANALYZE (PostgreSQL only, read-only queries).
