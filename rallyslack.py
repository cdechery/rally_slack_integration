#!/usr/bin/env python

import sys
from datetime import datetime
from datetime import timedelta
from pyral import Rally
from slacker import Slacker

DEBUG = False
if len(sys.argv) > 1:
	if sys.argv[1] == '-debug' or sys.argv[1] == '--debug':
		DEBUG = True


slack = Slacker('xxxxxx')

server="rally1.rallydev.com"

#as we are using an API key, we can leave out the username and password
user="xxx"
password="xxxxx"

workspace="workspace NAME, not ID"
project="project NAME, not ID"
#apikey="xxxxxxx"

#which slack channel does this post to?
channel = "#rally"

#Assume this system runs (via cron) every 15 minutes.
interval = 60 * 60

#format of the date strings as we get them from rally
format = "%Y-%m-%dT%H:%M:%S.%fZ"

#create the rally service wrapper
rally = Rally(server, user, password, workspace=workspace, project=project)

#build the query to get only the artifacts (user stories and defects) updated in the last day
querydelta = timedelta(days=-1)
querystartdate = datetime.utcnow() + querydelta
query = 'LastUpdateDate > ' + querystartdate.isoformat()

tags_to_exclude = ['some','tags','toignore']

response = rally.get('Artifact', fetch=True, query=query, order='LastUpdateDate desc')
for artifact in response:

	for exclude_tag in tags_to_exclude:
		if exclude_tag in artifact.Tags:
			continue

	include = False

	#start building the message string that may or may not be sent up to slack
	postmessage = '*' + artifact.FormattedID + '*'
	owner = artifact.CreatedBy.DisplayName.replace('[AD] ', '')
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
					postmessage = postmessage  + "> " + formated_date+' '+item + ' \n'
					include = True

	if include:
		postmessage = postmessage + 'https://rally1.rallydev.com/#/search?keywords=' + artifact.FormattedID + '\n'
		if DEBUG:
			print(postmessage)
		else:
			slack.chat.post_message(channel=channel, text=postmessage, username="rallyslackbot", as_user=False)
