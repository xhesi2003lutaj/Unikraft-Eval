
# Measures how fast memcached responds to individual get and set operations
memtier_benchmark -p 11211 -t 4 -c 50 -n 10000 --protocol=memcache_text
