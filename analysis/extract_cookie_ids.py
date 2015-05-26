# This module is used to extract persistent cookie IDs
# Version 3: Updated for proper HTTP Cookie Parsing
import cookie_util
from collections import defaultdict
import sqlite3 as lite
import datetime

# HELPER FOR EXTRACT_PERSISTENT_IDS_FROM_DBS
# goes through a cookie value string and attempts to break them down into parameter-value pairs
# based on a few known delimiters; adds these pairs to the raw cookie value dictionary
# currently uses two known delimiters
def add_inner_cookie_parameters(raw_cookie_dict, domain, name, value):
    delimiters = [":", "&"]  # currently known inner cookie delimiters
    for delimiter in delimiters:
        parts = value.split(delimiter)

        for part in parts:
            params = part.split("=")

            if len(params) == 2 and params[0] != '' and params[1] != '':
                raw_cookie_dict[(domain, name + "#" + params[0])].append(params[1])

# EXTRACTS PERSISTENT COOKIES FROM A MULTIPLE DATABASES DATABASE
# returns a dictionary with keys = (domain, name) pairs; values = values of the corresponding cookie
# values must be from non-shorted lived cookies (life at least <num_days> days long)
def extract_persistent_ids_from_dbs(cookie_dbs, num_days=30):
    for cookie_db in cookie_dbs:
        conn = lite.connect(cookie_db)
        curr = conn.cursor()

        # add all cookie-value pairs to a dictionary, provided these cookies live at least <days> days
        raw_cookie_dict = defaultdict(list)  # maps (domain, names) to lists of values
        
        for domain, name, value, access, expiry \
                in curr.execute("SELECT domain, name, value, accessed, expires FROM http_cookies WHERE http_type = 'response'"):

            # ignores cookies with blank or incomplete measurements
            if domain == '' or name == '' or value == '':
                continue

            # ignores session cookies
            if expiry is None:
                continue
            
            # prune away cookies with expiry times under a month
            expiry = datetime.datetime.strptime(expiry, "%Y-%m-%d %H:%M:%S")
            access = datetime.datetime.strptime(access.split('.')[0], "%Y-%m-%d %H:%M:%S")
            if (expiry - access).days < num_days:
                continue

            # add the full value strings then attempt to parse and add nested values as well
            raw_cookie_dict[(domain, name)].append(value)
            add_inner_cookie_parameters(raw_cookie_dict, domain, name, value)

    # only keep cookies with values that remain constant throughout the crawl
    final_cookie_dict = {}
    for cookie in raw_cookie_dict:
        if cookie_util.all_same(raw_cookie_dict[cookie]):
            final_cookie_dict[cookie] = raw_cookie_dict[cookie][0]

    conn.close()
    return final_cookie_dict

# EXTRACTS LIKELY IDS EXTRACTED FROM MULTIPLE DATABASES
# strings are flagged as id's if
# 1. they have the same lengths
# 2. the cookie appears in at least two different crawls (otherwise, we can't make a definitive statement)
# 3. they are at least <short_cutoff> and no more than <long_cutoff> characters long
# 4. the ids are pairwise dissimilar enough (as defined by the <sim> parameter
# returns a dictionary with domains as keys and the various cookie names as a value list
def extract_common_id_cookies(cookie_id_dicts, short_cutoff=6, long_cutoff=100, sim=0.45):
    raw_id_dict = defaultdict(list)  # for each cookie, a list of the values across each crawl

    # build up a dictionary consisting of all values seen for a given cookie
    for cookie_id_dict in cookie_id_dicts:
        for cookie in cookie_id_dict:
            raw_id_dict[cookie].append(cookie_id_dict[cookie])  # appending the id

    # prune away cookies that fail one of our unique ID heuristics
    final_cookie_id_dict = defaultdict(list)  # for each domain, list of candidate ID cookies
    for cookie in raw_id_dict:
        # i.e. any of our heuristics is failed
        if len(raw_id_dict[cookie]) <= 1 \
                or len(raw_id_dict[cookie][0]) < short_cutoff \
                or len(raw_id_dict[cookie][0]) > long_cutoff \
                or not cookie_util.all_same_len(raw_id_dict[cookie]) \
                or not cookie_util.all_dissimilar(raw_id_dict[cookie], sim):
            continue

        final_cookie_id_dict[cookie[0]].append(cookie[1])

    return final_cookie_id_dict

# MAPS KNOWN ID COOKIES WITH THEIR ACTUAL ID VALUES FROM A DB INSTANCE
# given a dictionary of persistent ids, goes through a database
# and returns a dictionary with the persistent ids and their unique values
# in the database (for those that actually appear)
def extract_known_cookies_from_db(db_name, cookie_id_dict):
    conn = lite.connect(db_name)
    cur = conn.cursor()

    found_cookies = {}
    
    for domain, name, value in cur.execute("SELECT domain, name, value FROM http_cookies WHERE http_type = 'response'"):

        # ignore blank values
        if domain == '' or name == '' or value == '':
            continue

        # match up with the value strings
        if domain in cookie_id_dict and name in cookie_id_dict[domain]:
            found_cookies[(domain, name)] = value  # first, match up the basic cookies

            # next, look for potential nested cookies
            if "=" in value:
                for delimiter in ["&", ":"]:
                    parts = value.split(delimiter)

                    for part in parts:
                        params = part.split("=")

                        if len(params) == 2 and name + "#" + params[0] in cookie_id_dict[domain] \
                                and params[0] != '' and params[1] != '':
                            found_cookies[(domain, name + "#" + params[0])] = params[1]
    conn.close()
    return found_cookies

# MAPS IDS TO THE COOKIES ON WHICH IT APPEARS
# reads in a dictionary from extract_known_cookies_from_db
# builds a new dictionary where each key is a unique id and each value is a list of the cookies that have that value
def map_ids_to_cookies(known_cookies):
    id_dict = defaultdict(list)

    for cookie in known_cookies:
        id_dict[known_cookies[cookie]].append(cookie)

    return id_dict

def get_id_values(DB, id_cookies_path):
    """
    Grab the identifying cookie values for this specific database
    """
    # load the dict of id cookies
    # this will be a defaultdict with default: 'list'
    id_cookies = cPickle.load(open(id_cookies_path))

    # NOTE: manually add a couple known identifying cookies that are not
    # flagged as identifying due to their structure. A better approach for ID
    # extraction is future work
    id_cookies['.doubleclick.net'] = 'id'
    id_cookies['.scorecardresearch.com'] = 'UID'

    # Check for hash names
    for k,v in id_cookies.iteritems():
        for value in v:
            if '#' in value and value.split('#')[0] not in id_cookies[k]:
                id_cookies[k].append(value.split('#')[0])

    # Load the database
    con = sqlite3.connect(DB)
    cur = con.cursor()

    # Extract identifying value strings for this db
    id_values = set()
    cur.execute("SELECT domain, name, value FROM http_cookies WHERE http_type = 'response'")
    for domain, name, value in cur.fetchall():
        if id_cookies.has_key(domain) and name in id_cookies[domain]:
            id_values.add(value)

            # Look for potential nested cookies
            if "=" in value:
                for delimiter in ["&", ":"]:
                    for part in value.split(delimiter):
                        params = part.split("=")

                        if (len(params) == 2 and name + "#" + params[0] in id_cookies[domain]
                                and params[0] != '' and params[1] != ''):
                            id_values.add(params[1])
    con.close()
    
    return id_values
