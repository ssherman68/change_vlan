change_vlan.py

Original version Stacy Sherman 3/22/17
Last update Stacy Sherman 3/22/17

This script uses netmiko functions to log in to a Cisco switch & change
All ports in VLAN X to VLAN Y. Assumes the switch is on an older version
of IOS and does not require the use of IOS-XE type Python APIs

gets list of VLANs from show int status
uses textfsm to parse out the status and ports of the VLAN ID in question
changes all ports on that VLAN to new_vlan

requires a textfsm file in the same directory to tell textfsm how to parse
the output of the show int status command

Currently this is interactive and it handles one switch at a time from user
input.

I would like to update so that:
  It can take a list of switches from a file
  It will ask if there are any other switches and use the same login