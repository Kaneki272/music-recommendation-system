# ADR 0004: Why Apache Kafka

## Context
A scalable recommendation engine requires processing thousands of user interaction events per second to update online learning models and analytics dashboards in near real-time.

## Decision
We chose Apache Kafka for our event streaming backbone.

## Consequences
- **Pros:** Extremely high throughput, durable storage of streams, allows decoupled microservices.
- **Cons:** High operational complexity (requires Zookeeper/Kraft), steep learning curve.
