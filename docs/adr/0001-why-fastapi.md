# ADR 0001: Why FastAPI

## Context
We need a robust, high-performance web framework for the backend of the Music Recommendation System.

## Decision
We chose FastAPI.

## Consequences
- **Pros:** Native asynchronous support, auto-generated OpenAPI documentation, high performance (Starlette/Pydantic), strict typing which reduces bugs in production.
- **Cons:** Younger ecosystem compared to Django, meaning some enterprise plugins might need to be built in-house.
