"""
==============================================================================
-- Rules and Assumptions for cookie linking --
 * All requests for a single top-level domain occur on the same IP
    - Can link requests by url/ref chains
 * Requests that occur for different top-level domains may occur on different
   days and thus can't be linked by IP
    - Can't use url/ref to link
    - Can link through an identifying cookie
 * Requests to HTTPS domains are not visible to adversary
 * Responses from HTTPS requested domains are not visible to adversary

==============================================================================
"""     
from urlparse import urlparse
import cPickle
import sqlite3
import networkx
import random
import os
import math
from scipy import stats

import identity_parser
from build_cookie_table import build_http_cookie_table
from extract_cookie_ids import get_id_values

def build_graph(con, id_values, user_id, random_sample = False, site_limit = 10000):
    """
    Build the graph based on the rules above for the specified user.
    The user_id == crawl_id in the database.

    @type con: sqlite3.Connection
    @type id_values: list
    @type user_id: number
    @type site_limit: number
    @type random_sample: boolean
    """
    cur = con.cursor()
    
    # New graph for this user
    print "\n===========================================\n"
    print "Creating graph for user %i" % user_id
    G = networkx.Graph()

    #Sample the top level sites to include in this graph
    if random_sample:
        cur.execute(("SELECT DISTINCT top_url FROM http_requests "
                    "WHERE crawl_id = ? "
                    "ORDER BY RANDOM() "
                    "LIMIT ?"), (user_id, site_limit,))
    else:
        cur.execute(("SELECT DISTINCT top_url FROM http_requests "
                    "WHERE crawl_id = ? "
                    "ORDER BY id "
                    "LIMIT ?"), (user_id, site_limit,))
    sampled_sites = set()
    for item in cur.fetchall():
        sampled_sites.add(item[0])

    clustered_sites = set()
    
    #HTTP Requests
    cur.execute(("SELECT r.url, r.referrer, r.top_url, c.name, c.value, r.in_us "
                "FROM http_requests r LEFT OUTER JOIN http_cookies c "
                "ON r.id = c.header_id AND c.http_type = 'request'"
                "WHERE r.crawl_id = ? "
                "AND r.top_url IN ({seq}) ".format(seq=','.join(['?']*len(sampled_sites)))),
                [user_id] + list(sampled_sites))

    for url, ref, top_url, name, value, in_us in cur.fetchall():
        if not top_url.endswith('/'): top_url += '/'
        if not url.endswith('/'): url += '/'
        if not ref.endswith('/'): ref += '/'
        clustered_sites.add(top_url)

        # Skip requests which are HTTPS as info is not seen
        if url.startswith('https'):
            continue

        # Add in URL nodes and connect if ref non-empty
        url_node = ("URL", url, top_url)
        G.add_node(url_node)
        if ref != '':
            ref_node = ("URL", ref, top_url)
            G.add_node(ref_node)
            G.add_edge(url_node, ref_node, in_us=in_us)

        # Add COOKIE node if value is identifying
        if value is not None and value in id_values:
            cookie_node = ("COOKIE", value)
            G.add_node(cookie_node)
            G.add_edge(cookie_node, url_node, in_us=in_us)

    #HTTP Response Set Cookies
    cur.execute(("SELECT r.url, r.referrer, r.top_url, c.domain, c.name, c.value, r.in_us "
                "FROM http_responses as r, http_cookies as c "
                "WHERE r.id = c.header_id "
                "AND c.http_type = 'response' "
                "AND r.crawl_id = ? "
                "AND r.top_url IN ({seq}) ".format(seq=','.join(['?']*len(sampled_sites)))),
                [user_id] + list(sampled_sites))

    for url, ref, top_url, domain, name, value, in_us in cur.fetchall():
        if not top_url.endswith('/'): top_url += '/'
        if not url.endswith('/'): url += '/'
        if not ref.endswith('/'): ref += '/'
        clustered_sites.add(top_url)
        
        # Skip requests which are HTTPS as info is not seen
        if url.startswith('https'):
            continue

        # Add COOKIE nodes if identifying
        if value in id_values:
            cookie_node = ("COOKIE", value)
            url_node = ("URL", url, top_url)
            G.add_node(url_node)
            G.add_node(cookie_node)
            G.add_edge(cookie_node, url_node, in_us=in_us)
    
    #HTTP Response Redirects
    cur.execute(("SELECT r.url, r.location, r.top_url, r.in_us "
                "FROM http_responses as r "
                "WHERE location IS NOT NULL "
                "AND location != '' "
                "AND r.crawl_id = ? "
                "AND r.top_url IN ({seq}) ".format(seq=','.join(['?']*len(sampled_sites)))),
                [user_id] + list(sampled_sites))

    for url, loc, top_url, in_us in cur.fetchall():
        if not top_url.endswith('/'): top_url += '/'
        if not url.endswith('/'): url += '/'
        if not loc.endswith('/'): loc += '/'
        clustered_sites.add(top_url)

        # Skip requests which are HTTPS as info is not seen
        if url.startswith('https'):
            continue

        # Link redirect to url
        if loc.startswith('http'):
            url_node = ("URL", url, top_url)
            loc_node = ("URL", loc, top_url)
            G.add_node(url_node)
            G.add_node(loc_node)
            G.add_edge(loc_node, url_node, in_us=in_us)
    
    return G, clustered_sites

def get_GCC(G, top_urls):
    """
    Returns the connected component with the largest number of
    top urls
    """
    comps = networkx.connected_component_subgraphs(G)
    comps = sorted(comps, key=len, reverse=True)
    return comps[0]

def percentage_in_GCC(G, sampled_sites):
    """
    Returns the percentage of sites that embed third parties 
    which are in the GCC
    """
    top_urls = set(sampled_sites)
    leaking_urls = identity_parser.get_leaking_sites()

    # Find the percentage of these sites which are in GCC
    GCC = get_GCC(G, top_urls)
    if GCC is None: return 0
    if len(top_urls) == 0: return 0
    GCC = filter(lambda x : x[0] == "URL", GCC)
    urls_in_gcc = set()
    for item in GCC: urls_in_gcc.add(item[1])

    #### Count the number of urls with the same hostname in the GCC
    #for item in GCC: urls_in_gcc.add(urlparse(item[1]).hostname)
    #top_urls = set()
    #for item in sampled_sites:
    #    top_urls.add(urlparse(item).hostname)
    
    difference = top_urls.difference(urls_in_gcc)
    counter = 0
    for url in urls_in_gcc:
        for leak_url in leaking_urls:
            if urlparse(url).hostname == urlparse(leak_url).hostname:
                counter += 1
    num_leakers = len(leaking_urls.intersection(urls_in_gcc))
    percent = float(len(top_urls) - len(difference))/len(top_urls)
    print "Identity leakers in GCC: " + str(num_leakers)
    print "Identity leakers hostnames in GCC: " + str(counter)
    print "Percent of sites in GCC: " + str(percent)
    return percent, num_leakers

def percentage_US(G, sampled_sites, in_us=1):
    """
    Filters the graph to nodes that pass the US check and
    returns the percentage in GCC seen by an adversary
    that can see only US traffic.
    """
    # Generate a subgraph with only nodes that enter US
    subgraph_edges = filter(lambda x: x[2]['in_us'] == in_us, G.edges(data=True))
    subgraph_edges = [x[0:2] for x in subgraph_edges] # remove data
    subgraph = networkx.Graph(subgraph_edges) # graph with just these edges/nodes
    
    return percentage_in_GCC(subgraph, sampled_sites)

def get_site_sample(sites, size, random_order):
    """
    Returns a list of the top_urls for subgraph creation
    """
    if size >= len(sites):
        return sites

    if random_order:
        sampled_sites = random.sample(sites, size)
    else:
        max_starting_index = len(sites) - size - 1
        starting_index = random.randint(0, max_starting_index)
        sampled_sites = sites[starting_index:starting_index+size]
    return sampled_sites

def order_sequential_sites(con, user_id, sampled_sites):
    cur = con.cursor()
    cur.execute(("SELECT DISTINCT top_url FROM http_requests "
                "WHERE crawl_id = ? "
                "ORDER BY id "), (user_id,))
    top_urls = list()
    for top_url, in cur.fetchall():
        if not top_url.endswith('/'): top_url += '/'
        if top_url in sampled_sites:
            top_urls.append(top_url)
    return top_urls

def generate_samples(DB, id_cookies_path, random_order = False):
    """
    Generate subgraphs for each user picking top level sites at random or sequentially
    for a range of subgraph sizes. These subgraphs can be averaged for the paper's plots

    It's a bit messy, but comment/uncomment to run the general % in GCC analysis or % in US analysis
    """
    id_values = get_id_values(DB, id_cookies_path)
    con = sqlite3.connect(DB)
    cur = con.cursor()
    num_samples = 50

    # Save the raw output in pickle files
    name = DB.split('/')
    name = name[len(name)-1].split('.')[0]

    leaks = list()
    percents = list()
    # Build graph for each user in this DB
    for crawl_id in xrange(1, 26):
        x = range(10, 200, 5)
        y = list()
        G, sampled_sites = build_graph(con, id_values, crawl_id)
        if not random_order:
            sampled_sites = order_sequential_sites(con, crawl_id, sampled_sites)
        for i in x:
            print i
            for j in range(num_samples):
                # Generate a subgraph from the first graph
                subgraph_sites = get_site_sample(sampled_sites, i, random_order)
                subgraph_nodes = filter(lambda x : x[0] == 'URL' and x[2] in subgraph_sites, G.nodes())
                subgraph_nodes.extend(filter(lambda x : x[0] == 'COOKIE', G.nodes()))
                subgraph = G.subgraph(subgraph_nodes)
                percent, num_leakers = percentage_in_GCC(subgraph, subgraph_sites) #XXX - GCC analysis
                #percent, num_leakers = percentage_US(subgraph, subgraph_sites, in_us = (not 'US' in name)) #XXX - US analysis
                y.append(percent)

                # Real time analysis
                leaks.append(num_leakers)
                percents.append(percent)

        ### Save the data to disk ###
        
        #XXX - GCC analysis
        if random_order:
            cPickle.dump((x, y, num_samples), open('../data/random/'+name+'_'+str(crawl_id)+'_raw_data.pkl', 'wb'))
        else:
            cPickle.dump((x, y, num_samples), open('../data/sequential/'+name+'_'+str(crawl_id)+'_raw_data.pkl', 'wb'))
        
        #XXX - US analysis
        #if 'IE' in name:
        #    loc = 'ireland/'
        #elif 'JP' in name:
        #    loc = 'japan/'
        #elif 'US' in name:
        #    loc = 'us/'
        #else:
        #    print "Only makes sense to run this analysis for JP or IE"
        #    return
        #if random_order:
        #    cPickle.dump((x, y, num_samples), open('../data/'+loc+'random/'+name+'_'+str(crawl_id)+'.pkl', 'wb'))
        #else:
        #    cPickle.dump((x, y, num_samples), open('../data/'+loc+'sequential/'+name+'_'+str(crawl_id)+'.pkl', 'wb'))

    # Temporary analysis
    conf_int(percents)
    conf_int(leaks)

def conf_int(samples):
    n, min_max, mean, var, skew, kurt = stats.describe(samples)
    conf_interval = stats.t.interval(0.95,len(samples)-1, loc=mean, scale=math.sqrt(var)/math.sqrt(len(samples))) 
    print "Average = " + str(mean)
    print "Error = " + str(conf_interval[1] - mean)

if __name__ == '__main__':
    import sys
    import data
    DB = sys.argv[1]
    print "Processing DB: " + DB
    
    # Make sure this db has http_cookie table
    build_http_cookie_table(DB)
    
    generate_samples(DB, data.id_cookies_path, random_order=True)
