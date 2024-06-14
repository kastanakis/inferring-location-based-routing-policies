Prerequisites: python3, pybgpstream, pytricia, bogons, geolite
Datasets: as-graph-caida, anycast-prefixes-bgptools, bogons-cymru, peeringdb-snapshot, routing-tables-bgpstream

We want to geolocate all neighbors of an AS and suggest a method to update the AS relationships dataset with an extra column: the location(s) where two ASes peer.

Step 1: Find all neighbors of a given AS from AS relationships
Step 2: Geolocate all neighbors' geographical presence using Maxmind from Ripestat
Step 3: Geolocate all neighbors' peering locations using PeeringDB
Step 4: Compile a dataset with all possible locations where a neighbor can peer with the given AS

Validate with simulations: run simulations with the vanilla AS relationships and the location-aware AS relationships
Validate with real Cloudflare data.
