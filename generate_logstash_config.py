#!/usr/bin/env python

import requests
import json

# Ignore providers - these ipset providers should be ignored
ignoreproviders = [
]

# Ignore categories - categories we dont want to use
ignorecategories = [
  'unroutable',       # This will include private address space, and we will match against internal data which includes pridate address space
  'geolocation',      # Geolocation data
  'organizations',    # Includes mostly known good hosts
]

def score(category):
  if category == "attacks":
    return -10
  else:
    return -1

r = requests.get("http://iplists.firehol.org/all-ipsets.json")
ipsets = json.loads(r.content)

output = "input {"

for ipset in ipsets:
  # Ignore providers
  if ipset['maintainer'] in ignoreproviders:
    continue
  # Ignore categories
  if ipset['category'] in ignorecategories:
    continue

  name = "%s %s" % (ipset['maintainer'], ipset['ipset'])
  shortname = ipset['ipset']
  category = ipset['category']
  reputation_score = score(category)

  info_url = "http://iplists.firehol.org/%s.json" % shortname
  request = requests.get(info_url)
  ipset_info = json.loads(request.content)

  url = ipset_info['file_local']

  # Ignore ipsets without a URL to download
  if url == "":
    continue

  output += '''
  http_poller {
    urls => {
      1 => "%s"
    }
    request_timeout => 180
    interval        => 3600
    codec           => line
    type            => iplist
    add_field       => {
      "[database][name]"              => "%s"
      "[database][shortname]"         => "%s"
      "[database][category]"          => "%s"
      "[database][reputation_score]"  => "%s"
    }
    tags            => [ 'ipdatabase' ]
  }''' % (url, name, shortname, category, reputation_score)

output += "\n}"

print output.encode('utf-8')
