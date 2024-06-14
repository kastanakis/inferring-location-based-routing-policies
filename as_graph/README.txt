asrank-download.py is a more complex Python script that can be used as-is to download all the ASNs, organizations, or ASN links. 
The following arguments will cause the script to download all the asns, organizations, and asnLinks into their respective files.

python3 asrank-download.py -v -a asns.jsonl -o organizations.jsonl -l asnLinks.jsonl -u https://api.asrank.caida.org/v2/graphql

