import sys
import os
import subprocess32
subprocess = subprocess32
import re

def runNSLookup(hostname):
    # Run nslookup on host
    scratchFilePath = os.path.join(os.path.dirname(__file__),'scratch_file.txt')
    scratchFile = open(scratchFilePath, 'w')
    cmd = [ "nslookup", hostname ]
    subprocess.call(cmd, stdout=scratchFile, timeout=300)
    scratchFile.close()
    scratchFile = open(scratchFilePath, 'r')
    NSLookupResult = scratchFile.read()
    scratchFile.close()
    return NSLookupResult

def parseNSLookup(NSLookupResult):
    ips = set()
    non_authoritative_answer = False
    for line in NSLookupResult.split("\n"):
        line = line.strip()
        if not non_authoritative_answer and line != 'Non-authoritative answer:':
            continue
        else:
            non_authoritative_answer = True
        if line[0:8] == 'Address:':
            address = re.sub('Address:\s','',line)
            ips.add(address)
    return ips

def runDig(hostname):
    scratchFilePath = os.path.join(os.path.dirname(__file__),'scratch_file.txt')
    scratchFile = open(scratchFilePath, 'w')
    cmd = [ "dig", "@8.8.8.8", "+trace", hostname, "A" ]
    subprocess.call(cmd, stdout=scratchFile, timeout=300)
    scratchFile.close()
    scratchFile = open(scratchFilePath, 'r')
    digResult = scratchFile.read()
    scratchFile.close()
    return digResult

def getCname(hostname, digOutput):
    cnames = [ ]
    resolvedNames = set()
    resolvedIPs = set()
    for digLine in digOutput.split("\n"):
        digLine = digLine.strip()
        digLine = re.sub("[ \t]+", "\t", digLine)
        digLineTokens = digLine.split("\t")
        if len(digLineTokens) != 5:
            continue
        if digLineTokens[2].strip() == "IN":
            if digLineTokens[3].strip() == "A":
                resolvedNames.add(digLineTokens[0].strip()[:-1])
                resolvedIPs.add(digLineTokens[4].strip())
            elif digLineTokens[3].strip() == "CNAME" and digLineTokens[0].strip()[:-1] == hostname:
                cnames.append(digLineTokens[4].strip()[:-1])
    if len(cnames) > 0 and not cnames[0] in resolvedNames:
        return cnames[0], resolvedIPs
    return "", resolvedIPs

# Do the DNS lookup using dig 
# starts at the root name severs
def getDigIPs(hostname):
    resolved_ips = set()
    try:
        hostname = hostname.strip()
        if hostname == '':
            pass
        digOutput = runDig(hostname)
        
        cnameCount = 0
        cname = hostname
        while cnameCount < 3:
            cname, resolved = getCname(cname, digOutput)
            resolved_ips = resolved_ips.union(resolved)
            if cname == "":
                    break
            digOutput = runDig(cname)
            cnameCount = cnameCount + 1
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass
    return resolved_ips

# Do the DNS lookup using nslookup (faster)
def getIPs(hostname):
    resolved_ips = set()
    try:
        hostname = hostname.strip()
        if hostname == '':
            pass
        nsLookupOutput = runNSLookup(hostname)
        resolved_ips = parseNSLookup(nsLookupOutput)
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        pass
    return resolved_ips
