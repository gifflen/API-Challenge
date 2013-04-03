"""
Write a script that clones a server (takes an image and deploys the image as a new server).
"""
__author__ = 'Bruce Stringer'
import pyrax
import os
import datetime
from novaclient import exceptions
import time


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


#Loading credentials from ini file
def auth(credential_location="~/.rackspace_cloud_credentials"):
    """
    Loads the pyrax credentials from ~/.rackspace_cloud_credentials
    :param credential_location: The location containing the credential ini
    :return:
    """
    credentials = os.path.expanduser(credential_location)
    pyrax.set_credential_file(credentials)

    #Creating cloudserver client
    return pyrax.cloudservers


def select_server_from_list(cs):
    """
    Offers the user a list of servers to select from based on the passed client
    :param cs: A pyrax cloudserver client object with its auth already initialized.
    :return: A server object based on the selection
    """
    servers = cs.servers.list()
    for num in range(len(servers)):
        print num, ") Server name:", servers[num].name, "  -- ID:", servers[num].id

    choice = get_int_input("Which server would you like to clone? (by number) ")

    if 0 <= choice <= len(servers):
        return servers[choice]
    else:
        print choice
        print "Invalid Choice."
        select_server_from_list(cs)


def create_image(server, image_name=""):
    """
    Creates an image of the given server.
    :param server: A valid Server object
    :param image_name: The desired name for the image.
    :return: The uuid of the generated image. :raise: Any exceptions generated from the client
    """
    if image_name == "":
        image_name = str(server.name) + " " + str(datetime.datetime.now())

    try:
        image_uuid = server.create_image(image_name)
    except exceptions.ClientException:
        raise

    print "Creating image: ", image_name
    return image_uuid


def clone_server(cs, image_uuid, name="clone", flavor_id=2):

    new_image = cs.images.get(image_uuid)

    if new_image._info['status'] == 'SAVING':
        print "Image is currently " + str(new_image._info['progress']) + "% complete."
        return None

    return cs.servers.create(name, image_uuid, flavor_id)


def print_server_info(server):
    print "Server Name: " + server.name
    print "Root Password: " + server.adminPass
    for network_type, networks in server.networks.iteritems():
        if networks is not None:
            for address in networks:
                print "Networks: " + network_type + " " + address


def main():
    cs = auth()
    image_uuid = None
    while image_uuid is None:
        server = select_server_from_list(cs)
        try:
            image_uuid = create_image(server)
        except exceptions.ClientException as e:
            print "Unable to create image at this time: " + e.message

    clone = None
    while clone is None:
        clone = clone_server(cs, image_uuid, name=server.name + "-clone", flavor_id=server._info['flavor']['id'])
        if clone is None:
            time.sleep(10)

    print_server_info(clone)

if __name__ == '__main__':
    main()
