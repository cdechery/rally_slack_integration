import os
import requests
import json
import sys
from datetime import datetime
from datetime import timedelta
from pytz import timezone
from pyral import Rally
import ConfigParser
import pytz

config = ConfigParser.RawConfigParser()

# attempt to read the settings file
try:
    path = os.path.dirname(os.path.realpath(__file__))
    config.read(path + '/settings.ini')
except Exception:
    print('Error reading settings.ini file')
    exit(1)

rally_username = config.get('Credentials', 'rally_username')
rally_password = config.get('Credentials', 'rally_password')

server = config.get('RallySettings', 'server')

DEBUG = False
if len(sys.argv) > 1:
    if sys.argv[1] == '-debug' or sys.argv[1] == '--debug':
        DEBUG = True

#the slack Webhook URL
webhook_url = config.get('SlackSettings', 'webhook_url')

# POST header
header = {"Content-type": "application/json",
          "Accept": "text/plain"}

user=rally_username
password=rally_password
#apikey="_Mgm47nNTvWxfcqSooWHiNj2dbOWBUO0qDHodcjAb0"

workspace=config.get('RallySettings','workspace')
project=config.get('RallySettings','project')

#which slack channel does this post to?
channel = config.get('RallySettings','channel')

#get interval from config
interval = float( config.get('General', 'interval') )

#the timezone
localtz = timezone( config.get('General', 'timezone') )

#format of the date strings as we get them from rally
format = "%Y-%m-%dT%H:%M:%S.%fZ"

#create the rally service wrapper
rally = Rally(server, user, password, workspace=workspace, project=project)

#build the query to get only the artifacts (user stories and defects) updated in the last day
querydelta = timedelta(days=-1)
querystartdate = datetime.utcnow() + querydelta
query = 'LastUpdateDate > ' + querystartdate.isoformat()

tags_to_exclude = config.get('RallySettings','tags_to_exclude').split(',')

response = rally.get('Artifact', fetch=True, query=query, order='LastUpdateDate desc')
for artifact in response:

    contains_tag = False

    for exclude_tag in tags_to_exclude:
        for tag in artifact.Tags:
            if exclude_tag.strip() == tag.Name:
                contains_tag = True

    if contains_tag:
        continue

    include = False

    #start building the message string that may or may not be sent up to slack
    owner = artifact.CreatedBy.DisplayName.replace('[AD] ', '')
    postmessage = '*' + artifact.FormattedID + '*'
    postmessage = postmessage + ': ' + artifact.Name + ' (Owner: '+owner+') \n'

    for revision in artifact.RevisionHistory.Revisions:

        revisionDate = datetime.strptime(revision.CreationDate, format)
        age = revisionDate - datetime.utcnow()
        seconds = abs(age.total_seconds())

        #only even consider this story for inclusion if the timestamp on the revision is less than iterval seconds onld
        if seconds < interval:
            description = revision.Description
            items = description.split(',')

            tz_date = timezone('UTC').localize(revisionDate).astimezone( tz=localtz )
            formated_date = tz_date.strftime('%H:%M:%S')

            for item in items:
                item = item.strip()
                #the only kinds of updates we care about are changes to OWNER and SCHEDULE STATE
                #other changes, such as moving ranks around, etc, don't matter so much
                if item.startswith('SCHEDULE STATE ') or item.startswith("OWNER added "):
                    postmessage = postmessage  + "> " + formated_date +' '+item + ' \n'
                    include = True

    if include:
        postmessage = postmessage + 'https://rally1.rallydev.com/#/search?keywords=' + artifact.FormattedID + '\n'
        if DEBUG:
            print(postmessage)
        else:
            payload = { 'text': postmessage }
            #print(payload)
            response = requests.post(webhook_url, json=payload, headers=header)
            print(response.status_code, response.reason)
