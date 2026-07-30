# ADR 0003: Why PostgreSQL

## Context
We require a database for highly structured, transactional data with strict schema enforcement such as user account credentials, financial/billing records, and static relational music catalog data.

## Decision
We chose PostgreSQL.

## Consequences
- **Pros:** ACID compliance, rock-solid reliability, powerful JOIN capabilities.
- **Cons:** Scaling out horizontally requires more effort compared to NoSQL alternatives.
