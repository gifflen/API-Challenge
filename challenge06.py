"""
Write a script that creates a CDN-enabled container in Cloud Files.
"""
__author__ = 'Bruce Stringer'

import pyrax
import os


def auth(credential_location="~/.rackspace_cloud_credentials"):
    """
    Loads the pyrax credentials from ~/.rackspace_cloud_credentials
    :param credential_location: The location containing the credential ini
    :return:
    """
    credentials = os.path.expanduser(credential_location)
    pyrax.set_credential_file(credentials)


def create_cloudfiles_container(cf, name):
    container = cf.create_container(name)
    print "Created container: " + name
    return container


def get_int_input(message="Enter an integer: "):
    """
    Gets a valid int input from the user. If a valid integer is not entered, get_int_input calls itself again.
    :param message: The message to be displayed to the user when gathering input.
    :return: A valid integer
    """
    try:
        choice_str = input(message)
        choice = int(choice_str)
        return choice
    except (ValueError, SyntaxError, NameError):
        print "Invalid Input"
        get_int_input(message)


def get_str_input(message="Enter a string: "):
    """
   Gets a valid str input from the user. If a valid integer is not entered, get_int_input calls itself again.
   :param message: The message to be displayed to the user when gathering input.
   :return: A valid integer
   """
    try:
        input_str = raw_input(message)
        if input_str == "":
            get_str_input(message)
        return input_str
    except (ValueError, SyntaxError, NameError):
        print "Invalid Input"
        get_str_input(message)


def select_container_from_list(cf, message="Please select a container by number: "):
    """
    Offers the user a list of containers to select from based on the passed client
    :param cf: A pyrax cloudserver client object with its auth already initialized.
    :return: A cloudfiles object based on the selection
    """
    containers = cf.get_all_containers()
    for num in range(len(containers)):
        print num, ") Server name:", containers[num].name, "  -- Object Count: ", containers[num].object_count

    print str(len(containers)), ") Create new container"
    choice = get_int_input(message)
    cont = None
    if 0 <= choice <= len(containers) - 1:
        cont = containers[choice]
    elif choice == len(containers):
        while cont is None:
            name = get_str_input("Please enter the name for the new cloud files container: ")
            cont = create_cloudfiles_container(cf, name)
    else:
        print "Invalid Choice: ", choice
        select_container_from_list(cf)

    return cont


def main():
    auth()

    cf = pyrax.cloudfiles

    container = select_container_from_list(cf, "Select which container you would like to CDN enable: ")
    print "You've selected: " + container.name

    ttl = get_int_input("What would you like your CDN ttl set to in seconds (Ex. 900): ")
    container.make_public(ttl=ttl)

    print "CDN enabled on: ", container.name

if __name__ == "__main__":
    main()
