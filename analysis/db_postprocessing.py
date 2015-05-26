# A set of utilities to add the necessary fields to a fresh crawl database
from urlparse import urlparse
import geoip2.database
import sqlite3
import os
import re

from ip_util import getOrganization
import haversine

def add_host_col(db, table = 'http_requests'):
    con = sqlite3.connect(db)
    cur = con.cursor()
    
    try:
        cur.execute("ALTER TABLE %s ADD COLUMN host VARCHAR (500)" % table)
        con.commit()
    except sqlite3.OperationalError:
        pass

    cur.execute("SELECT id, url FROM %s" % table)
    counter = 0
    for resp_id, url in cur.fetchall():
        hostname = urlparse(url).hostname
        cur.execute("UPDATE %s SET host = ? WHERE id = ?" % table, (hostname, resp_id))
        counter += 1

        if counter > 0 and counter % 10000 == 0:
            con.commit()
            print "[HOST] - " + str(counter) + " added..."

    con.commit()
    con.close()

def add_org_col(db):
    con = sqlite3.connect(db)
    cur = con.cursor()
    
    try:
        cur.execute("ALTER TABLE traceroutes ADD COLUMN org VARCHAR(500)")
        con.commit()
    except sqlite3.OperationalError:
        pass

    cur.execute("SELECT DISTINCT ip FROM traceroutes")
    counter = 0
    for ip, in cur.fetchall():
        organization = getOrganization(ip)
        cur.execute("UPDATE traceroutes SET org = ? WHERE ip = ?", (organization, ip))
        counter += 1

        if counter > 0 and counter % 100 == 0:
            con.commit()
            print "[IP] - " + str(counter) + " added..."

    con.commit()
    con.close()

def add_geo_check(db):
    # Open a connection to geolocation db
    reader = geoip2.database.Reader('../collection/GeoLite2-City.mmdb')
    
    # Define EC2 locations
    if 'JP' in db:
        ec2_reg = 'JP'
        ec2_lat = 35.689506
        ec2_lon = 139.6917
    elif 'IE' in db:
        ec2_reg = 'IE'
        ec2_lat = 53.347778
        ec2_lon = -6.259722
    else:
        ec2_reg = 'US'
        ec2_lat = 39.0900
        ec2_lon = -77.6400

    c = 299.792458 # speed of light in vacuum - km/ms
    n = 1.52 # reference index of refraction for fiber
    v = c/n # speed of light in fiber - km/ms
    
    # Open connection to database
    con = sqlite3.connect(db)
    cur = con.cursor()
    cur_loop = con.cursor()

    # Add a new column for results
    try:
        cur.execute("ALTER TABLE http_requests ADD COLUMN in_us BOOLEAN")
        cur.execute("ALTER TABLE http_responses ADD COLUMN in_us BOOLEAN")
        cur.execute("ALTER TABLE traceroutes ADD COLUMN min_rtt REAL")
        cur.execute("ALTER TABLE traceroutes ADD COLUMN geo_check BOOLEAN")
        con.commit()
    except sqlite3.OperationalError:
        pass

    # calc minimum rtts for every ip in traceroute
    counter = 0
    
    cur_loop.execute("SELECT DISTINCT ip, time FROM traceroutes")
    for ip, time in cur_loop.fetchall():
        # Get lat/lon for this IP from maxmind
        try:
            response = reader.city(ip)
        except geoip2.errors.AddressNotFoundError:
            continue
        
        # Do country check if city is not available
        if ec2_reg == 'US' and response.country.iso_code == 'US': # Assume okay
            lat = ec2_lat
            lon = ec2_lon
        elif response.city.name is None and response.country.iso_code == 'US':
            if ec2_reg == 'US': # Assume okay
                lat = ec2_lat
                lon = ec2_lon
            elif ec2_reg == 'JP': # Use Portland
                lat = 45.52
                lon = -122.681944
            elif ec2_reg == 'IE': # Use NYC
                lat = 40.7127
                lon = -74.0059
        else: # Use returned lat/lon
            lat = response.location.latitude
            lon = response.location.longitude
        
        if lat == None or lon == None:
            continue

        # Time of flight as the crow flies
        distance = haversine.distance((ec2_lat, ec2_lon), (lat, lon)) #in km
        rtt = 2 * float(distance)/v
        passed = float(time) > rtt

        # Update table with results of check
        cur.execute("UPDATE traceroutes SET geo_check = ?, min_rtt = ?, \
                    country = ?, iso_code = ? WHERE ip = ? AND time = ?", 
                    (passed, rtt, response.country.name, 
                    response.country.iso_code, ip, time))
        counter += 1
        
        if counter > 0 and counter % 100 == 0:
            con.commit()
            print "[GEOIPCHECK -- Trace] - " + str(counter) + " added..."
    con.commit()

    if ec2_reg != 'US':
        cur.execute("UPDATE http_requests SET in_us = 1 WHERE host IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code = 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_responses SET in_us = 1 WHERE host IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code = 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_requests SET in_us = 0 WHERE host NOT IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code = 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_responses SET in_us = 0 WHERE host NOT IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code = 'US' AND geo_check = 1)")
    else:
        cur.execute("UPDATE http_requests SET in_us = 0 WHERE host IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code != 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_responses SET in_us = 0 WHERE host IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code != 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_requests SET in_us = 1 WHERE host NOT IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code != 'US' AND geo_check = 1)")
        cur.execute("UPDATE http_responses SET in_us = 1 WHERE host NOT IN \
                    (SELECT DISTINCT hostname FROM traceroutes \
                    WHERE iso_code != 'US' AND geo_check = 1)")

    con.commit()
    con.close()

if __name__ == '__main__':
    from data import *

    DBS = [Alexa_US, Alexa_IE, Alexa_JP, AOL_https, AOL_ghostery, AOL_never, AOL_no_blocking, AOL_from_visited, AOL_DNT]

    for DB in DBS:
        print "Processing database: %s" % DB

        # Make sure this db has http_cookie table
        add_host_col(DB, 'http_requests')
        add_host_col(DB, 'http_responses')

        # Add a column of organizations
        add_org_col(DB)

        #Add geo-inconsistency check
        add_geo_check(DB)
