Cookies That Give You Away: The Surveillance Implications of Web Tracking
=========================================================================

This is the public code release for our WWW 2015 paper. You can find the paper 
[here](http://www.cs.princeton.edu/~ste/papers/www15_cookie_surveil.pdf) and the 
data [here](https://webtransparency.cs.princeton.edu/cookiesurveillance/).

Data Collection
---------------

The measurements were taken on three Amazon EC2 instances using [OpenWPM](https://github.com/citp/OpenWPM)
v0.1, which is included [in this repo](https://github.com/englehardt/cookies-that-give-you-away/tree/master/collection/automation).

* `collection`
    * `run_crawl.py` - Run a specific crawl, settings should be changed here
        for each configuration.
    * `run_network_measurment.py` - Run after the crawl, on the same instance. 
        This will do DNS lookups for each unique hostname seen during the 
        crawl and run a traceroute to each.
    * `make_profiles.py` - Create Alexa profiles by randomly subsampling the
        respective top alexa sites
    * `make_full_list.py` - Create `union_of_sites.txt`, a list of sites to
        feed into synchronized crawls for ID detection.
    * `profiles` - Contains the 25 AOL profiles used in the paper, as well as
        three Alexa models
    * `automation` - OpenWPM v0.1
* `analysis`
    * `create_id_dict.py` - Will extract ID cookies using two SQLite databases
        created through a synchronized crawl, as described in Section 4.5 of the
        paper.
    * `create_graph.py` - Builds cookie linking graph based on parameters set
        in `generate_samples()`, as described in section 4.6 of the paper.
    * `db_postprocessing.py` - Adds several columns to the crawl databases,
        including the geocheck described in Section 4.4 of the paper.
    * `build_cookie_table.py`/`Cookie.py` - Parses HTTP Request/Response
        headers to pull out cookies. Integrated into the more recent releases of
        OpenWPM. 
        * NOTE: `Cookie.py` is included in the python standard library, but its
        parsing rules are nowhere near what is used in practice. The version here is 
        heavily modified. I recommend using
        [cookies.py](https://github.com/sashahart/cookies), which is based on 
        [RFC 6265](http://tools.ietf.org/html/rfc6265).
