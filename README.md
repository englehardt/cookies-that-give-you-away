Cookies That Give You Away: The Surveillance Implications of Web Tracking
=========================================================================

This is the public code release for our WWW 2015 paper. You should also check
out [the paper](https://senglehardt.com/papers/www15_cookie_surveil.pdf),
[the presentation](https://senglehardt.com/presentations/2015_05_www_cookies_that_give.pdf),
and [the data](https://github.com/englehardt/cookies-that-give-you-away#data).

Data Collection
---------------

The measurements were taken on three Amazon EC2 instances using [OpenWPM](https://github.com/citp/OpenWPM)
v0.1, which is included [in this repo](https://github.com/englehardt/cookies-that-give-you-away/tree/master/collection/automation).

* `run_crawl.py` - Run a specific crawl, settings should be changed here
    for each configuration. Only a single configuration from the paper is
    included here.
* `run_network_measurment.py` / `get_dns.py` / `get_traceroute.py` -
    Run after the crawl, on the same instance.
    This will do DNS lookups for each unique hostname seen during the
    crawl and run a traceroute to each.
* `make_profiles.py` - Create Alexa profiles by randomly subsampling the
    respective top alexa sites from `alexa_top_500_{IE,JP,US}.txt`.
* `make_full_list.py` - Create `union_of_sites.txt`, a list of sites to
    feed into synchronized crawls for ID detection.
* `profiles` - Contains the 25 AOL profiles used in the paper, as well as
    three Alexa models as pickled Python objects.
* `automation` - OpenWPM v0.1

Data Analysis
-------------

* `create_id_dict.py` / `cookie_util.py` / `extract_cookie_ids.py` -
    Will extract ID cookies using two SQLite databases created through
    a synchronized crawl, as described in Section 4.5 of the paper.
* `create_graph.py` - Builds cookie linking graph based on parameters set
    in `generate_samples()`, as described in section 4.6 of the paper.
* `db_postprocessing.py` / `haversine.py` - Adds several columns to the crawl
    databases, including the geocheck described in Section 4.4 of the paper.
* `build_cookie_table.py` / `Cookie.py` - Parses HTTP Request/Response
    headers to pull out cookies. Integrated into the more recent releases of
    OpenWPM.
    * NOTE: `Cookie.py` is included in the python standard library, but its
    parsing rules are nowhere near what is used in practice. The version here is
    heavily modified. I recommend using
    [cookies.py](https://github.com/sashahart/cookies), which is based on
    [RFC 6265](http://tools.ietf.org/html/rfc6265).
* `identity_parser.py` - parses and prints statistics on identity leakers given
    in `identity_leaks.txt`

Data
----

* **Crawl Data** are available as bzip2 compressed SQLite databases. Each database contains measurement data for 25 simulated users.
    The following test cases are available for download:
    * [surveil_alexa_IE.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_alexa_IE.sqlite.bz2) - The Ireland location with the Alexa browsing model.
    * [surveil_alexa_JP.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_alexa_JP.sqlite.bz2) - The Japan location with the Alexa browsing model.
    * [surveil_alexa_US.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_alexa_US.sqlite.bz2) - The United States location with the Alexa browsing model.
    * [surveil_aol_dnt.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_dnt.sqlite.bz2) - DNT = 1 with the AOL browsing model (US location)
    * [surveil_aol_from_visited.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_from_visited.sqlite.bz2) -
        ["Accept third-party cookies: From Visited"](https://support.mozilla.org/en-US/kb/disable-third-party-cookies) set in Firefox with the AOL browsing model (US location)
    * [surveil_aol_ghostery.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_ghostery.sqlite.bz2) - [Ghostery](https://www.ghostery.com/en/) installed with all possible trackers blocked using the AOL model (US location)
    * [surveil_aol_https-everywhere.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_https-everywhere.sqlite.bz2) - [HTTPS Everywhere](https://www.eff.org/HTTPS-EVERYWHERE) installed with AOL browsing model (US location)
    * [surveil_aol_never.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_never.sqlite.bz2) -
        ["Accept third-party cookies: Never"](https://support.mozilla.org/en-US/kb/disable-third-party-cookies) set in Firefox with the AOL browsing model (US location)
    * [surveil_aol_no_blocking.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_aol_no_blocking.sqlite.bz2) - US location with AOL browsing model with no blocking options set (used as baseline)
    * [surveil_id_detection_roman.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_id_detection_roman.sqlite.bz2) and [surveil_id_detection_triton.sqlite.bz2](https://webtransparency.cs.princeton.edu/cookiesurveillance/surveil_id_detection_triton.sqlite.bz2) - Two databases which crawl `union_of_sites.txt` with no blocking from the United States location for use in ID detection.
* `GeoLite2-City.mmdb` - available for download [here](http://dev.maxmind.com/geoip/geoip2/geolite2/)
* `identity_leaks.txt` - Data collected from manual study of identity leakers as described
    in Section 4.7 of the paper
