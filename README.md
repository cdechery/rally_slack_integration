# New Rally-Slack Integration Script

Based on a previous forked script, my version offers some key improvements:
* Moved (most) settings and (all) credentials to a separate file
* Allow for DEBUG mode so you can change whatever you want in the message and test it out before pushing it to Slack
* Changed the integration to Slack Apps instead of relying on a Slack Token, since Legacy tokens on Slack are soon to be phased-out
