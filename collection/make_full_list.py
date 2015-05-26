# This script aggregates all of the urls we may visit
# for the purpose of ID detection
import cPickle
import os

PROFILE_LOC = os.path.join(os.path.dirname(__file__),'profiles/')

urls = set()

# Scan the AOL profiles
for i in xrange(25):
    profile = cPickle.load(open(PROFILE_LOC+str(i)+'.p','rb'))
    sites = profile.values()[0]
    for site in sites:
        urls.add(site)

# Scan the alexa profiles
COUNTRIES = ['US', 'JP', 'IE']
for COUNTRY in COUNTRIES:
    ALEXA_PROFILES = os.path.join(PROFILE_LOC,'alexa_'+COUNTRY+'.p')
    profiles = cPickle.load(open(ALEXA_PROFILES, 'rb'))
    for i in xrange(25):
        sites = profiles[i]
        for site in sites:
            urls.add(site)

# Write the unique list of urls to an output file
with open('union_of_sites.txt', 'w') as f:
    for url in urls:
        f.write(url + '\n')
