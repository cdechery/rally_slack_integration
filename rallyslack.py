#!/usr/bin/env python

#note, you'll need to be running python2 (built with 2.7, python DOES NOT WORK )
#you'll need to pip install pyral (the python-rally connector) as slacker (the slack connector)

import sys
from datetime import datetime
from datetime import timedelta
from pyral import Rally
from slacker import Slacker
import ConfigParser

config = ConfigParser.RawConfigParser()

try:
	config.read('settings.ini')
except Exception:
	print('Error reading settings.ini file')
	exit(1)

slack_api_key = config.get('Credentials', 'slack_api_key')
rally_username = config.get('Credentials', 'rally_username')
rally_password = config.get('Credentials', 'rally_password')

DEBUG = False
if len(sys.argv) > 1:
	if sys.argv[1] == '-debug' or sys.argv[1] == '--debug':
		DEBUG = True

slack = Slacker( slack_api_key )

server=config.get('RallySettings','server')

#as we are using an API key, we can leave out the username and password
user=rally_username
password=rally_password

workspace=config.get('RallySettings','workspace')
project=config.get('RallySettings','project')
#apikey="_Mgm47nNTvWxfcqSooWHiNj2dbOWBUO0qDHodcjAb0"

#which slack channel does this post to?
channel = config.get('RallySettings','channel')

#Assume this system runs (via cron) every hour
interval = 60 * 60

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

	for exclude_tag in tags_to_exclude:
		if exclude_tag.strip() in artifact.Tags:
			continue

	include = False

	#start building the message string that may or may not be sent up to slack
	owner = artifact.CreatedBy.DisplayName.replace('[AD] ', '')
	postmessage = '*' + artifact.FormattedID + '*'
	postmessage = postmessage + ': ' + artifact.Name + ' (Owner: '+owner+') \n'

	for revision in artifact.RevisionHistory.Revisions:
		revisionDate = datetime.strptime(revision.CreationDate, format)
		formated_date = revisionDate.strftime('%d/%m/%Y %H:%M:%S')
		age = revisionDate - datetime.utcnow()
		seconds = abs(age.total_seconds())
		#only even consider this story for inclusion if the timestamp on the revision is less than iterval seconds onld
		if seconds < interval:
			description = revision.Description
			items = description.split(',')

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
			slack.chat.post_message(channel=channel, text=postmessage, username="rallyslackbot", as_user=False)
