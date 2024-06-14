import geoip2.database

def geolocate_per_ip(ip):
    with geoip2.database.Reader('input/GeoLite2-City_20240119/GeoLite2-City.mmdb') as city_reader:
        # response_asn = asn_reader.asn(ip)
        response_country = city_reader.city(ip)
        # pprint(response_asn)
        return response_country