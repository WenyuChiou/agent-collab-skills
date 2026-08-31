# Optional recall and canonical memory

External memory or recall systems are optional caches. They may accelerate
search, but they never become the policy, evidence, or decision authority.

## Authority order

1. current human instruction and recorded decision;
2. repository state and immutable acceptance evidence;
3. validated checkpoint and canonical append-only memory events;
4. optional recall cache.

## Write path

An agent may create a proposal under `.coord/memory-proposals/`. It cannot
directly add, change, archive, supersede, or delete canonical memory.

1. Create a proposal with evidence references and an action hash.
2. Record a human `approve`, `decline`, or `revise` decision.
3. If approved and bytes still match the action hash, append a new event.
4. Keep older events immutable. Resolutions and corrections reference them.
5. Update an optional recall cache only after the canonical event exists.

Cache failure never changes a human decision or turns a failed task into
success. Cache writes and external service mutations require the host's normal
permission and audit controls.
