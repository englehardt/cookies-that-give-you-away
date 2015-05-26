import cPickle
import random
import os

COUNTRY = 'IE'
PROFILE_LOC = os.path.join(os.path.dirname(__file__),'profiles/')
ALEXA_LIST = os.path.join(os.path.dirname(__file__),'alexa_top_500_'+COUNTRY+'.txt')

# Import the alexa sites
alexa_sites = list()
with open(ALEXA_LIST, 'r') as f:
    for line in f:
        alexa_sites.append('http://'+line.strip().lower())

# Random sample 25 times
profiles = dict()
for i in xrange(25):
    sites = random.sample(alexa_sites, 200)
    profiles[i] = sites

# Save the pickle file
cPickle.dump(profiles,open(PROFILE_LOC+'alexa_'+COUNTRY+'.p', 'wb'))
