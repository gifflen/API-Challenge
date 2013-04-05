"""
- Create 2 servers, supplying a ssh key to be installed at /root/.ssh/authorized_keys.
- Create a load balancer
- Add the 2 new servers to the LB
- Set up LB monitor and custom error page.
- Create a DNS record based on a FQDN for the LB VIP.
- Write the error page html to a file in cloud files for backup.
"""
from __future__ import with_statement
from urlparse import urlparse
import pyrax
import os
import re
import time
import sys


__author__ = 'Bruce Stringer'


class DomainParts(object):
    def __init__(self, domain_parts, tld):
        self.domain = None
        self.subdomains = None
        self.tld = tld
        if domain_parts:
            self.domain = domain_parts[-1]
            if len(domain_parts) > 1:
                self.subdomains = domain_parts[:-1]

    def base_domain(self):
        return self.domain + "." + self.tld


def get_domain_parts(url, tlds):
    urlElements = urlparse(url).hostname.split('.')
    # urlElements = ["abcde","co","uk"]
    for i in range(-len(urlElements), 0):
        lastIElements = urlElements[i:]
        #    i=-3: ["abcde","co","uk"]
        #    i=-2: ["co","uk"]
        #    i=-1: ["uk"] etc

        candidate = ".".join(lastIElements)  # abcde.co.uk, co.uk, uk
        wildcardCandidate = ".".join(["*"] + lastIElements[1:])  # *.co.uk, *.uk, *
        exceptionCandidate = "!" + candidate

        # match tlds:
        if (exceptionCandidate in tlds):
            return ".".join(urlElements[i:])
        if (candidate in tlds or wildcardCandidate in tlds):
            return DomainParts(urlElements[:i], '.'.join(urlElements[i:]))
            # returns ["abcde"]

    raise ValueError("Domain not in global list of TLDs")


def auth(credential_location="~/.rackspace_cloud_credentials"):
    """
    Loads the pyrax credentials from ~/.rackspace_cloud_credentials
    :param credential_location: The location containing the credential ini
    :return:
    """
    credentials = os.path.expanduser(credential_location)
    pyrax.set_credential_file(credentials)


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


def create_servers(cloud_account, image_uuid="c195ef3b-9195-4474-b6f7-16e5bd86acd0", flavor_id="2", num_servers=0,
                   server_base_name="server", files=None):
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
        server_name = server_base_name
        if files is None:
            server = cloud_account.servers.create(server_name, image_uuid, flavor_id)
        else:
            server = cloud_account.servers.create(server_name, image_uuid, flavor_id, files=files)
        print "Creating server " + server_name

        #Adding the server object to the list of servers created
        servers.append(server)

        #Registering passwords in password dict. Storing the password with the UUID as the key.
        passwords[server.id] = server.adminPass
    return servers


def get_ssh_key():
    ssh_key_location = get_str_input("Please enter the location for the ssh key you would like to use: ")
    try:
        key_contents = open(ssh_key_location).read()
        return ssh_key_location, key_contents
    except IOError as e:
        print e.message
        print "Unable to access specified key: %s" % ssh_key_location
        get_ssh_key()
    return None


def isValidHostname(hostname):
    if len(hostname) > 255:
        return False
    if hostname[-1:] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def get_fqdn(tlds):
    domain = get_str_input("Please enter the FQDN to be used for your 2 new servers: ").lower()
    if not isValidHostname(domain):
        print "Invalid domain: %s" % domain
        get_fqdn(tlds)
    try:
        domain_parts = get_domain_parts("http://" + domain, tlds)
        if domain_parts.subdomains is None:
            print "Not a valid fqdn (EX sub.example.com): %s" % domain
            get_fqdn(tlds)

    except ValueError:
        print "invalid domain"
        get_fqdn(tlds)

    return domain_parts, domain


def create_node(lb_client, address, port=80):
    return lb_client.Node(address=address, port=port)


def create_load_balancer(lb_client, lb_name, port=80, protocol="HTTP", nodes=None, virtaul_ips=None):
    if not virtaul_ips:
        virtaul_ips = []
    if not nodes:
        nodes = []

    return lb_client.create(lb_name, port=port, protocol=protocol, nodes=nodes, virtual_ips=virtaul_ips)


def create_vip(lb_client):
    return lb_client.VirtualIP(type="PUBLIC")


def main():
    auth()

    cs_client = pyrax.cloudservers
    dns_client = pyrax.cloud_dns
    lb_client = pyrax.cloud_loadbalancers
    cf_client = pyrax.cloudfiles

    # load tlds, ignore comments and empty lines:
    with open("tlds.txt") as tldFile:
        tlds = [line.strip() for line in tldFile if line[0] not in "/\n"]

    valid_domain = False
    while not valid_domain:
        #get domain
        domain_parts, fqdn = get_fqdn(tlds)
        base_domain = domain_parts.base_domain()

        #Find domain
        try:
            domain = dns_client.find(name=base_domain)
        except pyrax.exc.NotFound:
            #TODO allow creation of domain
            print "There is no DNS information for the domain '%s'." % base_domain
            continue

        records = domain.list_records()
        valid_domain = True
        for record in records:
            if record.name.lower() == fqdn and record.type in ['A', 'CNAME']:
                print "Record for this FQDN %s already exists." % fqdn
                valid_domain = False

    print "\'%s\' selected." % fqdn

    key_location, key_contents = get_ssh_key()
    files = {
        '/root/.ssh/authorized_keys': key_contents
    }
    #create Servers with key
    servers = create_servers(cs_client, server_base_name=fqdn, files=files, num_servers=2)

    #Wait for servers' networks to be created
    print "Waiting for servers networks to be provisioned."
    network_configured = False
    while not network_configured:
        network_configured = True
        for server in servers:
            server.get()
            #print "Server Name: %s\t Id: %s\tStatus: %s\tProgress: %d" % (
            #   server.name, server.id, server.status, server._info['progress'])
            if 'private' not in server.networks:
                network_configured = False
            if server.status == "ERROR":
                print "Server failed to build, Exiting"
                sys.exit(2)
        if not network_configured:
            sys.stdout.write('.')
            time.sleep(30)

    #create nodes
    nodes = []
    for server in servers:
        print server.networks['private'][0]
        nodes.append(create_node(lb_client, server.networks['private'][0]))

    #create lb with nodes
    vip = create_vip(lb_client)

    lb = create_load_balancer(lb_client, fqdn, nodes=nodes, virtaul_ips=[vip])

    if not pyrax.utils.wait_until(lb, 'status', 'ACTIVE', interval=30, verbose=True):
        print "Creating the lb failed"
        sys.exit(3)

    print lb
    #setup LB monitor with custom error page

    #create dns record from lb VIP at FQDN

    #Write the error page html to a file in cloud files for backup.


if __name__ == "__main__":
    main()
