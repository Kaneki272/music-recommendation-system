# ADR 0002: Why MongoDB

## Context
We have unstructured and highly variable data such as detailed user listening logs, metadata from external APIs (Spotify), and dynamic ML feature tracking.

## Decision
We chose MongoDB as our primary document store.

## Consequences
- **Pros:** Schema flexibility, horizontal scalability, perfect for storing deeply nested JSON responses from Spotify and user profiles.
- **Cons:** Lack of strong ACID transactions across multiple collections.
