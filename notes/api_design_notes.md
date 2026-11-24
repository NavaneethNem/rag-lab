# Orders API design notes

## Token-bucket rate limits

Give each authenticated tenant a bucket with capacity 120 and a refill rate of 20 tokens per second. A normal request costs one token and a bulk export costs 12. An idle tenant can submit ten exports immediately. After those requests empty the bucket, another export needs 600 ms of refill time.

Use one atomic Redis operation to read the balance, apply elapsed refill time up to capacity, and deduct the request cost. Store fractional tokens so frequent requests preserve partial refills. Return HTTP 429 when the balance falls below the request cost and round the refill wait up to whole seconds for `Retry-After`.

## PostgreSQL connection pool budget

Set `max_connections` to 100 in this deployment and budget 20 connections for migrations, monitoring, and other clients. Allow six API replicas during a rolling deploy. The per-replica ceiling is `floor((100 - 20) / 6) = 13`.

Estimate steady-state demand as `ceil(peak_transactions_per_second * mean_hold_seconds / (replicas * target_utilization))`. At 800 transactions per second, a 40 ms mean hold time, four steady replicas, and 70% target utilization, the estimate is 12 connections per replica. Start there and track connection checkout latency and transaction hold time under load. Inspect session states with `SELECT state, count(*) FROM pg_stat_activity GROUP BY state;`.

## Redis cache invalidation

Use cache-aside reads with keys such as `orders:513:v42` and a 300-second TTL. Increment the order revision in the same PostgreSQL transaction that changes the order and record an invalidation event in the transactional outbox. After commit, a worker advances the cached revision and deletes the previous payload. Apply only newer revisions so duplicate or out-of-order deliveries are safe.

On a cache miss, populate the key for the revision read alongside the database row. A delayed fill for revision 42 can then only write to the old key after revision 43 becomes current. Serve read-after-write requests from PostgreSQL until the client's expected revision is visible in Redis.

## JWT refresh token rotation

Issue access JWTs with a 10-minute lifetime and give each refresh token family a 30-day absolute deadline. Validate the refresh JWT signature, issuer, audience, purpose, and expiration. Lock the family row and reject revoked families and unknown token hashes. If the presented hash is current, mark it spent and insert its successor's hash in the same transaction. Return the successor after commit and cap its expiry at the family deadline.

Retain spent token hashes through that deadline. If a valid, spent refresh token reappears, revoke the family and require sign-in. Clients should serialize refresh requests so concurrent retries do not trigger reuse detection.
