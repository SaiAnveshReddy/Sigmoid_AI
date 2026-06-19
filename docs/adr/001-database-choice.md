# ADR 001: Use DuckDB as the Analytical Data Store

**Date:** 2025-06-19  
**Status:** Accepted

## Context

We need a SQL-queryable store for CPG transaction data to support aggregations, time-series queries, and ML feature engineering. Options considered:

1. **PostgreSQL** — Production-grade RDBMS, requires a separate server process
2. **SQLite** — Embedded, but row-oriented; poor at analytical GROUP BY queries over millions of rows
3. **DuckDB** — Embedded analytical database; columnar storage; zero server overhead

## Decision

Use **DuckDB** for this skeleton.

## Rationale

| Factor | DuckDB | PostgreSQL | SQLite |
|--------|--------|-----------|--------|
| Server required | No | Yes | No |
| Analytical query speed | Excellent | Good | Poor |
| Python integration | Native | psycopg2 | Native |
| Docker complexity | None | Extra service | None |
| Production path | Migrate to PG | Already production | Not suitable |

DuckDB is ideal for a skeleton: zero infrastructure, excellent SQL support, and a clear migration path to PostgreSQL for production.

## Consequences

- **Positive:** Anyone can run the system with zero DB setup overhead
- **Positive:** Analytical queries (GROUP BY, window functions) are fast
- **Negative:** DuckDB is single-writer; for concurrent writes in production, migrate to PostgreSQL
- **Migration path:** Swap `src/ingestion/db.py` connection string; all SQL is ANSI-compatible
