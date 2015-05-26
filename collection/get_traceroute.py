import sys
import os
import subprocess32
subprocess = subprocess32
import re

# Do a traceroute
def runTraceroute(hostname):
    scratchFilePath = os.path.join(os.path.dirname(__file__),'scratch_file.txt')
    scratchFile = open(scratchFilePath, 'w')
    cmd = [ "traceroute", "-q", "1", "-m", "25", hostname ]
    subprocess.call(cmd, stdout=scratchFile, timeout=300)
    scratchFile.close()
    scratchFile = open(scratchFilePath, 'r')
    tracerouteResult = scratchFile.read()
    scratchFile.close()
    return tracerouteResult

# Parse traceroute result
def parseTraceroute(tracerouteResult):
    lines = tracerouteResult.split('\n')
    route = list()
    for i in xrange(1, len(lines)):
	result = lines[i].split(' ')
        if len(result) == 1: # end of list
            break
	if result[0] == '': # deal with alignment
	    result.remove('')
	if result[2] == '*': # no result
	    continue
	row = result[0]
	ip = re.sub('[()]','',result[3])
	time = result[5]
	route.append((row, ip, time))
    return route

# Do a full traceroute lookup
def getRoutes(hostname):
    route = list()
    try:
        hostname = hostname.strip()
        if hostname == '':
            pass
        output = runTraceroute(hostname)
        route = parseTraceroute(output)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass
    return route

if __name__=='__main__':
    result = runTraceroute('google.com')
    data = parseTraceroute(result)
    import ipdb; ipdb.set_trace()
