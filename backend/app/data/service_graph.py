"""
Static microservice dependency topology used by two consumers:

1. The synthetic generator (app/data/synthetic.py) picks a "root" service for
   each simulated incident and propagates symptom alerts to its neighbors.
2. The composite distance metric (app/pipeline/distance.py) looks up hop
   distance between two alerts' services to compute the `service_penalty`
   term — two alerts on adjacent services are more likely to be the same
   incident than two on unrelated services.

Real deployments would derive this graph from a service mesh / APM topology
API. For the hackathon prototype it's a fixed adjacency list that mirrors a
realistic e-commerce microservice architecture.
"""
from collections import deque
from functools import lru_cache

# Undirected adjacency list. Direction of the dependency doesn't matter for
# correlation purposes -- only "how many hops apart" does.
SERVICE_GRAPH = {
    "api-gateway": ["auth-service", "checkout-service", "search-service", "cdn-edge"],
    "auth-service": ["api-gateway", "user-db"],
    "user-db": ["auth-service"],
    "checkout-service": ["api-gateway", "payment-service", "inventory-service", "order-service", "cache-redis"],
    "payment-service": ["checkout-service", "payment-db"],
    "payment-db": ["payment-service"],
    "inventory-service": ["checkout-service", "inventory-db"],
    "inventory-db": ["inventory-service"],
    "order-service": ["checkout-service", "order-db", "shipping-service", "notification-service"],
    "order-db": ["order-service"],
    "shipping-service": ["order-service"],
    "notification-service": ["order-service"],
    "cache-redis": ["checkout-service"],
    "search-service": ["api-gateway", "recommendation-service"],
    "recommendation-service": ["search-service"],
    "cdn-edge": ["api-gateway"],
}

ALL_SERVICES = list(SERVICE_GRAPH.keys())

# Hop distance beyond which we treat services as "unrelated" (penalty = 1.0).
MAX_MEANINGFUL_HOPS = 3


@lru_cache(maxsize=None)
def hop_distance(service_a: str, service_b: str) -> int:
    """BFS shortest path length between two services. Unknown/disconnected -> large number."""
    if service_a == service_b:
        return 0
    if service_a not in SERVICE_GRAPH or service_b not in SERVICE_GRAPH:
        return MAX_MEANINGFUL_HOPS + 1

    visited = {service_a}
    queue = deque([(service_a, 0)])
    while queue:
        node, dist = queue.popleft()
        if node == service_b:
            return dist
        for neighbor in SERVICE_GRAPH.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return MAX_MEANINGFUL_HOPS + 1


def service_penalty(service_a: str, service_b: str) -> float:
    """Normalize hop distance to a 0-1 penalty. 0 = same service, 1 = unrelated/far."""
    hops = hop_distance(service_a, service_b)
    return min(hops / MAX_MEANINGFUL_HOPS, 1.0)


def neighbors_within(service: str, max_hops: int):
    """All services within `max_hops` of `service` (excluding itself), nearest first."""
    if service not in SERVICE_GRAPH:
        return []
    visited = {service}
    queue = deque([(service, 0)])
    ordered = []
    while queue:
        node, dist = queue.popleft()
        if dist > 0:
            ordered.append((node, dist))
        if dist >= max_hops:
            continue
        for neighbor in SERVICE_GRAPH.get(node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, dist + 1))
    return ordered
