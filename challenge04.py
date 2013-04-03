"""
Write a script that uses Cloud DNS to create a new A record when passed a FQDN and IP address as arguments.
"""
__author__ = 'Bruce Stringer'

import pyrax
import os
import socket


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


def get_ipaddr_input(message="Please enter a valid IPv4 Address:"):
    ip_addr = get_str_input(message)

    #IP validation
    try:
        socket.inet_aton(ip_addr)
    except socket.error:
        print "Invalid IP address"
        get_ipaddr_input()

    return ip_addr


def create_domain(dns_client, name, email):
    try:
        domain = dns_client.create(name=name, emailAddress=email)
        return domain
    except pyrax.exc.DomainCreationFailed as e:
        raise


def add_record(domain, fqdn, record_type, ip, priority="", ttl=300):
    record_types = ["A", "CNAME", "MX", "NS", "SRV", "TXT"]
    record_type = str(record_type).upper()
    if record_type not in record_types:
        raise ValueError("Not a valid record type.")
    elif ttl < 300 or ttl > 86400:
        raise ValueError("Invalid TTYL. Should be between 300 and 86400")

    record = {
        'type': record_type,
        'name': fqdn,
        'data': ip,
        'ttl': ttl,
    }

    if record_type == "MX":
        if priority < 0 or priority > 65535:
            raise ValueError("Invalid priority. Should be between 0 and 65535")
        record['priority'] = priority

    try:
        generated_record = domain.add_records(record)
    except (pyrax.exc.BadRequest,  pyrax.exc.DomainRecordAdditionFailed) as e:
        raise

    return generated_record


def select_dns_from_list(dns_client, message="Please select a domain by number: "):
    """
    Offers the user a list of domains to select from based on the passed client
    :param dns_client: A pyrax cloud dns client object with its auth already initialized.
    :return: A domain object based on the selection
    """
    domains = dns_client.list()
    for num in range(len(domains)):
        print num, ") Domain:", domains[num].name

    print str(len(domains)), ") Create new container"
    choice = get_int_input(message)
    domain = None
    if 0 <= choice <= len(domains) - 1:
        domain = domains[choice]
    elif choice == len(domains):
        while domain is None:
            name = get_str_input("Please enter the name for the new domain: ")
            email = get_str_input("Please enter your email address: ")
            try:
                domain = create_domain(dns_client, name, email)
            except pyrax.exc.DomainCreationFailed as e:
                print "Could not create domin: " + e.message
                select_dns_from_list(dns_client, message)
    else:
        print choice
        print "Invalid Choice."
        select_dns_from_list(dns_client)
    return domain


def main():
    record_type = "A"

    auth()

    dns_client = pyrax.cloud_dns

    domain = select_dns_from_list(dns_client)
    print "Domain: " + domain.name + " selected."

    ip = get_ipaddr_input(message="Please input a valid IPv4 address to point your record to: ")
    record = None
    while record is None:
        try:
            fqdn = get_str_input("Please enter the fqdn for the record you wish to add: ")
            record = add_record(domain, fqdn, record_type, ip)[0]
        except (pyrax.exc.BadRequest, pyrax.exceptions.DomainRecordAdditionFailed) as e:
            print "Adding domain failed: " + e.message

    print "Created record %s for %s at %s" % (record.type, record.name, record.data)

if __name__ == "__main__":
    main()
