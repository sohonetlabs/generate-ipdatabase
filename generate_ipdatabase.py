#!/usr/bin/env python

import os
import sys
import time
import datetime
import logging
import re
import json
import yaml
import getopt
import requests
from voluptuous import Schema, Required, MultipleInvalid, Invalid
from elasticsearch import Elasticsearch, helpers

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s', datefmt='%Y-%m-%dT%H:%M:%SZ')
logging.Formatter.converter = time.gmtime
logger = logging.getLogger(os.path.basename(__file__))

def getconfig(argv):
  try:
    opts, args = getopt.getopt(argv, "c:dh", ['config', 'help', 'debug'])
    if not opts:
      usage()
      sys.exit(2)
  except getopt.GetoptError:
    usage()
    sys.exit(2)

  for opt, arg in opts:
    if opt in ('-h', '--help'):
      usage()
      sys.exit(2)
    elif opt in ('-c', '--config'):
      configfile = arg
    elif opt in ('-d', '--debug'):
      logger.setLevel(logging.DEBUG)
    else:
      usage()
      sys.exit(2)

  logger.info("Reading config from %s" % configfile)
  with open(configfile, 'r') as file:
    config = yaml.load(file)

  configschema = {
    Required('elasticsearch_host'): str,
  }

  try:
    schema = Schema(configschema, extra=True)
    schema(config)
  except MultipleInvalid, e:
    print("Missing values from config file!")
    print(str(e))
    sys.exit(1)

  return config


def usage():
  print("%s -c <configfile> [--debug]" % os.path.basename(__file__))

# Generate reputation score based on category
def score(category, shortname):
  if category == "whitelist":
    return 100
  elif shortname in config['reputation_scores'].keys():
    return config['reputation_scores'][shortname]
  elif category == "attacks":
    return -10
  else:
    return -1

def handle():
  r = requests.get("http://iplists.firehol.org/all-ipsets.json")
  ipsets = json.loads(r.content)

  for ipset in ipsets:
    name = "%s %s" % (ipset['maintainer'], ipset['ipset'])
    shortname = ipset['ipset']
    category = ipset['category']

    # Ignore providers
    if ipset['maintainer'] in config['ignore_providers']:
      logger.info("Skipping %s due to matching ignore_providers" % name)
      continue
    # Ignore categories
    if category in config['ignore_categories']:
      logger.info("Skipping %s due to matching ignore_categories" % name)
      continue
    # Ignore databases
    if shortname in config['ignore_databases']:
      logger.info("Skipping %s due to matching ignore_databases" % name)
      continue


    info_url = "http://iplists.firehol.org/%s.json" % shortname
    info_request = requests.get(info_url)
    ipset_info = json.loads(info_request.content)

    url = ipset_info['file_local']

    # Ignore ipsets without a URL to download
    if url == "":
      continue

    request = requests.get(url)
    logger.info("Processing %s database" % name)
    update(request.content.split("\n"), name, shortname, category)

def update(data, name, shortname, category):
  client = Elasticsearch(ELASTICSEARCH_HOST)

  actions = []

  for line in data:
    if re.match("^#", line):
      continue
    if re.match("^\s*$", line):
      continue

    document = {
      '_index': ELASTICSEARCH_INDEX,
      '_type': 'ipdatabase',
      '_source': {
        '@timestamp': datetime.datetime.now().isoformat(),
        'database': {
          'name': name,
          'shortname': shortname,
          'category': category,
          'reputation_score': score(category, shortname),
        },
        'tags': [ 'ipdatabase' ],
      }
    }

    # Add either IPADDRESS or NETWORK+NETMASK fields depending if
    # entry is an IP address or CIDR range
    parts = line.split("/")
    if len(parts) == 1:
      ip = parts[0]
      document['_source']['IPADDRESS'] = ip
      document['_id'] = "%s-%s" % (ip, shortname)
    else:
      (network, netmask) = parts
      document['_source']['NETWORK'] = network
      document['_source']['NETMASK'] = netmask
      document['_id'] = "%s-%s-%s" % (network, netmask, shortname)

    actions.append(document)

  helpers.bulk(client, actions)

if __name__ == "__main__":
  global config
  config = getconfig(sys.argv[1:])

  DEBUG = False
  ELASTICSEARCH_HOST = config['elasticsearch_host']
  ELASTICSEARCH_PORT = config['elasticsearch_port'] if 'elasticsearch_port' in config else 9200
  ELASTICSEARCH_INDEX = config['elasticsearch_index']

  # Process whitelist
  if 'whitelist' in config:
    update(config['whitelist'], 'Custom Whitelist whitelist', 'whitelist', 'whitelist')

  # Process ipsets
  handle()

