"""
Write a script that builds three 512 MB Cloud Servers that following a similar naming convention.
(ie., web1, web2, web3) and returns the IP and login credentials for each server.
"""
__author__ = 'Bruce Stringer'
import pyrax
import os
import novaclient.v1_1.client as cs_client
import time


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


def get_flavor_by_ram(cs, ram_size):
    """
    Grabs a flavor based on a specific pyrax cloud server account and the image ram.
    :param cs: A pyrax cloudserver client object with its auth already initialized.
    :param ram_size: An int of the flavor's ram limit counted in MB. Ex. 512
    :return: Returns the first flavor found based on the flavor_size
    :raise: If no flavor is found a ValueError exception is raised.
    """

    #Checking to see if an appropriate Cloud server object was passed.
    if not isinstance(cs, cs_client):
        raise TypeError(cs, "Not a valid pyrax cloudserver client object")

    flavor = [flavor for flavor in cs.flavors.list() if flavor.ram == ram_size][0]

    if len(flavor) <= 0:
        raise ValueError("No valid flavor found with the size of : " + str(ram_size))

    return flavor


def create_servers(cloud_account, image_uuid="c195ef3b-9195-4474-b6f7-16e5bd86acd0", flavor_id="2", num_servers=0,
                   server_base_name="server"):

    """
    Creates a list of servers based on the given parameters.
    :param cloud_account: A pyrax client object with authentication configured.
    :param image_uuid: The uuid of the image to be provisioned from. Default Centos 6.3
    :param flavor_id: The resource flavor of the server to be provisioned. Default 512
    :param num_servers: The number of servers to provisions. Default 0
    :param server_base_name: The base name of all servers to be provisioned. Default  server
    :return: a list of server objects created and a dictionry of their admin passwords keyed by the server uuid.
    """
    servers = []
    passwords = {}

    #Iterating over the desired number of servers.
    for count in range(0, num_servers):
        server_name = server_base_name + str(count)
        server = cloud_account.servers.create(server_name, image_uuid, flavor_id)
        print "Creating server " + server_name

        #Adding the server object to the list of servers created
        servers.append(server)

        #Registering passwords in password dict. Storing the password with the UUID as the key.
        passwords[server.id] = server.adminPass
    return servers, passwords


def get_network_status(cs, server_list, polling_time=3):
    """
    Polls servers from the list
    :param cs: client object with authentication set
    :param server_list: List of server objects to check for network
    :param polling_time: The time in seconds to sleep between polling attempts
    :return: A list of server objects with complete network configuration
    """
    #Looping while the populated list is less than the list given.
    servers = []
    while len(servers) < len(server_list):
        #populating a list of servers that have their networks provisioned.
        servers = [cs.servers.get(server.id) for server in server_list if len(cs.servers.get(server.id).networks) > 0]
        time.sleep(polling_time)
        print "waiting"

    return servers


def print_server_info(server_list, passwords):
    """
    Prints server information based on the list of servers given
    :param server_list: A list of server type objects
    :param passwords: a dictionary with the server uuid as they key
    """
    for server in server_list:
        print "Server Name: " + server.name
        print "Root Password: " + passwords[server.id]
        for network_type, networks in server.networks.iteritems():
            if networks is not None:
                for address in networks:
                    print "Networks: " + network_type + " " + address
        print('===========================')


def main():
    #Setting Defaults
    servers_to_create = 3
    server_name = "apiserver"
    flavor_id = "2"
    image_uuid = "c195ef3b-9195-4474-b6f7-16e5bd86acd0"

    #Authorizing with cloud servers
    cs = auth()



    #Creating server based on Defaults
    servers, passwords = create_servers(cs, num_servers=servers_to_create, server_base_name=server_name,
                                        image_uuid=image_uuid, flavor_id=flavor_id)

    #collecting servers network information.
    print "Waiting for networks to be configured."
    servers = get_network_status(cs, servers)

    #display server information
    print_server_info(servers, passwords)


if __name__ == "__main__":
    main()
