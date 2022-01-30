#!/usr/bin/python

# change_vlan.py

# Original version Stacy Sherman 3/22/17
# Last update Stacy Sherman 3/22/17

# gets list of VLANs from show int status
# uses textfsm to parse out the status and ports of the VLAN ID in question
# changes all ports on that VLAN to new_vlan

# requires a textfsm file in the same directory to tell textfsm how to parse
# the output of the show int status command

# Currently this is interactive and it handles one switch at a time from user
# input.

# I would like to update so that:
#   It can take a list of switches from a file
#   It will ask if there are any other switches and use the same login

from netmiko import ConnectHandler
from textfsm import textfsm
from getpass import getpass
import socket
import dns.resolver


def select_vlans():

    # Allows user to interactively enter the vlan being replaced and the
    # vlan you want to replace it with

    print "\n\n"
    print "----------------------------------------------------------"
    print "|                                                        |"
    print "|                  VLAN Replacement Tool                 |"
    print "|                                                        |"
    print "----------------------------------------------------------"
    valid_resp = 0
    ans_int = -1
    orig_vlan = 0
    new_vlan = 0
    while valid_resp <= 1:
        if valid_resp == 0:
            print "\nPlease enter the VLAN you would like to replace (1 - 4096)\n"
        else:
            print "\nPlease enter the VLAN you would like to replace it with (1 - 4096):\n"
        print "Hit 'E' to exit\n"
        ans = raw_input("===> ")
        if ans.isdigit():
            ans_int = int(ans)
        else:
            ans_int = -1
        if ans in ['e', 'E']:
            print "\n Exiting..."
            return '0', '0'
        elif (valid_resp == 0) and (1 <= ans_int <= 4096):
            orig_vlan = ans
            valid_resp = 1
        elif (valid_resp == 1) and (1 <= ans_int <= 4096):
            new_vlan = ans
            return orig_vlan, new_vlan


def get_ip(in_str):

    # Takes an input string, test if it's a valid IPv4 address (using socket)
    # if not an IP address, assumes it's a  DNS name it needs to look up and
    # attempts to look up the name and return a string with the IP address
    # requires socket and dns libraries. Does not support IPv6

    DOMAIN = '.gnf.org'
    clean_str = in_str.strip()
    try:
        socket.inet_aton(clean_str)                        # Test if valid IP
        dev_ip = clean_str
    except socket.error:                                   # If not try DNS
        if clean_str.endswith(DOMAIN):
            name = clean_str                               # See if domain is
        else:                                              # there, append to
            name = clean_str + DOMAIN                      # name if not
        print "Looking up %s in DNS...\n" % name
        try:
            ans = dns.resolver.query(name)
            dev_ip = str(ans[0])
            print "found %s\n" % dev_ip
        except:
            print "Unable to find address for %s\n" % name # if can't find name
            dev_ip = ''                                    # return null str
    return dev_ip




def get_dev_info():

    # Gathers the IP address, username and password for the switch from the user
    # and returns a dictionary containing the needed information.
    # For now, it assumes the device type is Cisco_ios (not ASA, Juniper, etc)

    in_str = raw_input("\nName or IP address of device: ")
    ip_addr = get_ip(in_str)
    net_device = {}
    if ip_addr:
        username = raw_input("\nUser name: ")
        pwd = getpass()
        net_device = {
            'device_type': 'cisco_ios',
            'ip': ip_addr,
            'username': username,
            'password': pwd,
        }
    return net_device


def device_connect(net_device):

    # Connects to device, performs error checking (in the future) and prints out
    # confirmation information

    target_dev = {}
    try:
        target_dev = ConnectHandler(**net_device)      # Connect to device
        hostname = target_dev.find_prompt().strip('#')
        print "\nConnected to: %s at IP: %s \n" % (hostname, net_device['ip'])
        if target_dev.check_enable_mode:
            print "Enable mode verified\n"
        else:
            en = raw_input("You\'re not in enable mode. Enter \'y\' for enable: ")
            if en == 'y' or en == 'Y':
                target_dev.enable()
                if not target_dev.check_enable_mode:
                    print "Unable to enter enable mode.\n"
        target_dev.disable_paging()
    except:
        print "\nUnable to connect to %s\n" % net_device['ip']
    return target_dev


def get_int_status(device):

    # Runs a "show interface status" command on the switch, gets the information &
    # uses textfsm to parse the show interface status output
    # The argument 'template' is a file handle and 'intstat' is a
    # string with the command output
    # intstat_list will be a list of lists. A list for each interface containing:
    # [0]interface [1]description [2]status [3]VLAN [4]duplex [5]speed [6]interface type

    print "Getting interface status...\n"
    intstat = device.send_command('sh int status')  # intstat is unicode

    template = open("sh_int_status_parse.textfsm")
    re_table = textfsm.TextFSM(template)
    intstat_list = re_table.ParseText(intstat)
    print "Done.\n"
    return intstat_list


def get_int_vlan(intstat_list, vlan):

    # Takes the output of a show interface status and a desired VLAN
    # and returns a list with the interface names that are in that VLAN
    # NOTE: This only includes access interfaces, not trunk interfaces
    #
    # intstat_list: a list of lists. A list for each interface containing:
    # [0]interface [1]description [2]status [3]VLAN [4]duplex [5]speed [6]interface type
    # vlan: string w/ the desired VLAN ID (1 - 4096)
    # target_int: a list of interfaces set as an access port with that VLAN

    target_int = []
    x = 0
    for i in intstat_list:
        if intstat_list[x][3] == vlan:             # if the interface is in VLAN
            target_int.append(intstat_list[x][0])  # add the interface name to the list
        x += 1
    if len(target_int) == 0:
        print "No interfaces found in VLAN %s\n" % vlan
    return target_int


def replace_vlan(target_dev, target_int, new_vlan):

    # Runs IOS commands in to change all interfaces in the target_int list
    # to new_vlan

    return_val = 0
    cmd_list = []
    print "Changing the following interfaces to VLAN: %s:\n" % new_vlan
    for int_name in target_int:                # Cycle through interface list
        print "%s " % int_name                 # Display each interface to user
        cmd_list.append('interface ' +
                        int_name)             # Append the interface name
        cmd_list.append('switchport access vlan ' +
                        new_vlan)             # Append vlan change command
    confirm = ''
    while confirm not in ['Y', 'y', 'N', 'n']:
        confirm = raw_input('\nPlease type "y" to make changes or "n" to exit ==>')
    if confirm in ['Y', 'y']:
        print "Entering config mode...\n"
        target_dev.config_mode()
        print "Configuring interfaces...\n"
        out = target_dev.send_config_set(cmd_list)  # Send the vlan change commands
        if '%' in out:                              # If there's a '%' there might
                                                    # be a failure or warning
            print "There might be a problem. Last output was: %s\n" % out
            print "Changes were made but config will not be saved.\n"
            print "Please confirm all is OK and back out or save the config.\n"
        else:
            print "VLAN successfully set. \n"
            return_val = 1
        print "Exiting config mode...\n"
        target_dev.send_command('end')
        if return_val:                              # Save config if a change was
            print "Saving config...\n"                   # successfully made
            target_dev.send_command_expect('wr mem', '[OK]')
    else:
        print "\nExiting. No changes were made\n"
    print "Disconnecting...\n"
    target_dev.disconnect()                     # Close ssh conn. to device
    print "Done.\n"
    return return_val


def main():
    interactive = 1
    if interactive:
        old_vlan, new_vlan = select_vlans()
    if (old_vlan != '0') and (new_vlan != '0'):
        net_device = get_dev_info()               # Get the device info
        if net_device:
            target_dev = device_connect(net_device)   # Connect to device
            if target_dev:
                intstat_list = get_int_status(target_dev) # Get the show int status & parse into a list
                target_int = get_int_vlan(intstat_list, old_vlan)
                if target_int:
                    print "Replacing VLAN %s with VLAN %s in device %s\n" % (old_vlan, new_vlan, target_dev.ip)
                    replace_vlan(target_dev, target_int, new_vlan)


if __name__ == '__main__':
    main()