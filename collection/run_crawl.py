from automation import TaskManager
import cPickle
import random
import glob
import time
import os

NUM_BROWSERS = 1
COUNTRY = 'US' # Location of crawl: {US, IE, JP}
PROFILE_LOC = os.path.join(os.path.dirname(__file__),'profiles/')
ALEXA_PROFILES = os.path.join(PROFILE_LOC,'alexa_'+COUNTRY+'.p')

# Saves a crawl output DB to the data folder
db_loc = '../data/surveil_aol_dnt.sqlite'

# Load the default browser preferences
browser_params = TaskManager.load_default_params(NUM_BROWSERS)
preferences = browser_params[0]
preferences['disable_flash'] = False
preferences['headless'] = True

# Load the alexa profiles dict
# uncomment if running with Alexa profiles
#profiles = cPickle.load(open(ALEXA_PROFILES, 'rb'))

# Load the union of sites
# uncomment if running cookie ID detection
#sites = list()
#with open('union_of_sites.txt','r') as f:
#    for line in f:
#        sites.append(line.strip())

# Load the profile
for i in range(25):
    # Use AOL profiles
    # uncomment if running with AOL profiles
    profile = cPickle.load(open(PROFILE_LOC+str(i)+'.p','rb'))
    sites = profile.values()[0]

    # Use Alexa profiles
    # uncomment if running with Alexa profiles
    #sites = profiles[i]

    # Initialize the crawler
    manager = TaskManager.TaskManager(db_loc, browser_params, NUM_BROWSERS, PROFILE_LOC+str(i)+'.p')

    # Visit sites for the profile
    for site in sites:
        manager.get(site)

    # Shuts down the browsers and waits for the data to finish logging
    manager.close()
