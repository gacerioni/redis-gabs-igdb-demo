from prometheus_client import Counter, Histogram

# Define a counter for tracking cache hits and misses
CACHE_HITS = Counter('cache_hits', 'Number of cache hits')
CACHE_MISSES = Counter('cache_misses', 'Number of cache misses')

# Define a histogram to track request duration
REQUEST_DURATION = Histogram('request_duration_seconds', 'HTTP request duration in seconds')

# Define a counter with a label to distinguish between cache and DB hits
HITS = Counter('hits', 'Number of hits', ['type'])

# Define a histogram to track latencies with a label for the type of hit
LATENCY = Histogram('latency_seconds', 'Latency of cache and DB hits in seconds', ['type'])