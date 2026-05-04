Decision matrix:

| Check | Yes → add | No → skip |
|-------|-----------|-----------|
| Session p95 >5ms | + | — |
| Redis already deployed | + | — |
| Invalidation strategy ready (write-through) | + | — |

Add only if all three.
