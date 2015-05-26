import geoip2.database
import sqlite3
import urlparse
import os

from get_dns import getIPs
from get_traceroute import getRoutes

DB_NAME = '../data/surveil_aol_never.sqlite'

# Do geolocation
def geolocate(ip):
    try:
        response = reader.country(ip)
    except geoip2.errors.AddressNotFoundError:
        return None, None
    return response.country.name, response.country.iso_code

#Populates host column to HTTP requests, since headers aren't parsed
def add_host_column(con, cur):

    try:
        cur.execute("ALTER TABLE http_requests ADD COLUMN host VARCHAR (500)")
        con.commit()
    except sqlite3.OperationalError:
        pass
    
    request_ids = list()
    request_urls = list()
    cur.execute("SELECT id, url FROM http_requests")
    for item in cur.fetchall():
        request_ids.append(item[0])
        request_urls.append(item[1])

    counter = 0
    num_commits = 0
    for i in range(len(request_urls)):
        hostname = urlparse.urlparse(request_urls[i]).hostname
        cur.execute("UPDATE http_requests SET host = ? WHERE id = ?",(hostname, request_ids[i]))
        counter += 1

        if counter > 10000:
            con.commit()
            num_commits += 1
            print "[HOST] - " + str(num_commits*10000) + " out of " + str(len(request_urls)) + " committed"
            counter = 0
    con.commit()
    print "[HOST] - Complete"

# Open a connection to geolocation db
reader = geoip2.database.Reader('../data/GeoLite2-City.mmdb')

# Open the crawl database
database = os.path.expanduser(DB_NAME)
con = sqlite3.connect(database)
cur = con.cursor()

# Update the database
add_host_column(con,cur)
cur.execute("CREATE TABLE IF NOT EXISTS hostnames ( \
                id INTEGER PRIMARY KEY AUTOINCREMENT, \
                hostname VARCHAR (500), \
                ip VARCHAR (500), \
                country VARCHAR (500), \
                iso_code VARCHAR (10));")
cur.execute("CREATE TABLE IF NOT EXISTS traceroutes ( \
		id INTEGER PRIMARY KEY AUTOINCREMENT, \
		hostname VARCHAR (500), \
		row INTEGER, \
		ip VARCHAR (500), \
		time VARCHAR (100), \
                country VARCHAR (500), \
                iso_code VARCHAR (10));")
con.commit()

# Select the unique hostnames
hostnames = list()
cur.execute('SELECT DISTINCT host FROM http_requests')
for item in cur.fetchall():
    hostnames.append(item[0])

# Run a lookup on each host
counter = 0
index = 0
for hostname in hostnames:
    index += 1
    ip_set= getIPs(hostname)
    for ip in ip_set:
        country, iso_code = geolocate(ip)
        cur.execute("INSERT INTO hostnames (hostname, ip, country, iso_code) VALUES (?,?,?,?)",
                    (hostname, ip, country, iso_code))
        counter += 1

    if counter > 1000:
        con.commit()
        print "[LOOKUP] - " + str(index) + " out of " + str(len(hostnames)) + " processed"
        counter = 0

con.commit()
print "[LOOKUP] - Complete"

# Run a traceroute on each host
counter = 0
index = 0
for hostname in hostnames:
    index += 1
    route = getRoutes(hostname)
    for row in route:
        country, iso_code = geolocate(row[1])
        cur.execute("INSERT INTO traceroutes (hostname, row, ip, time, country, iso_code) VALUES (?,?,?,?,?,?)",
                    (hostname, row[0], row[1], row[2], country, iso_code))
        counter += 1

    if counter > 10:
        con.commit()
        print "[TRACEROUTE] - " + str(index) + " out of " + str(len(hostnames)) + " processed"
        counter = 0

con.commit()
print "[TRACEROUTE] - Complete"

# Close databases
reader.close()
con.close()
