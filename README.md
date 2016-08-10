# generate-ipdatabase

Generate or update an elasticsearch ipdatabase index from [Firehol iplists](http://iplists.firehol.org/) reputation databases

## Using it

Install the requirements by running ```pip install -r requirements.txt```

Copy example_config.yaml to config.yaml, and make any necessary modifications to the config file.

Run: ```./generate_ipdatabase.py -c config.yaml```

Schedule this command to run regularly to keep your index up-to-date.

## Index Template

Before running for the first time, import the included ```index-template.json``` into elasticsearch. This assumes the index will be called ```ipdatabase```, modify this setting if you're using a different name for the index.
