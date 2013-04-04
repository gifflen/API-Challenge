"""
Write a script that will create a static webpage served out of Cloud Files.
The script must create a new container, cdn enable it, enable it to serve an index file, create an index file object,
upload the object to the container, and create a CNAME record pointing  to the CDN URL of the container.
"""
__author__ = 'Bruce Stringer'

import pyrax
import os
from urlparse import urlparse


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


def create_cloudfiles_container(cf_client, name):
    container = cf_client.create_container(name)
    print "Created container: " + name
    return container


def create_index(container, content, index_name="index.html"):
    index = container.client.store_object(container, index_name, content)
    container.set_web_index_page(index_name)
    return index


def select_domain_from_list(dns_client, message="Please select a container by number: "):
    """
    Offers the user a list of domains to select from based on the passed client
    :param dns_client: A pyrax cloudserver client object with its auth already initialized.
    :return: A cloudfiles object based on the selection
    """
    domains = dns_client.list()
    for num in range(len(domains)):
        print num, ") Server name:", domains[num].name

    choice = get_int_input(message)
    domain = None
    if 0 <= choice <= len(domains) - 1:
        domain = domains[choice]
    else:
        print "Invalid Choice: ", choice
        select_domain_from_list(dns_client)

    return domain


def add_record(domain, fqdn, record_type, data, priority="", ttl=300):
    record_types = ["A", "CNAME", "MX", "NS", "SRV", "TXT"]
    record_type = str(record_type).upper()
    if record_type not in record_types:
        raise ValueError("Not a valid record type.")
    elif ttl < 300 or ttl > 86400:
        raise ValueError("Invalid TTYL. Should be between 300 and 86400")

    record = {
        'type': record_type,
        'name': fqdn,
        'data': data,
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


def main():
    auth()

    cf_client = pyrax.cloudfiles
    dns_client = pyrax.cloud_dns

    #create new container
    container_name = get_str_input("Please enter the name for your new container: ")
    container = create_cloudfiles_container(cf_client, container_name)

    #cdn enable container
    ttl = get_int_input("What would you like your CDN ttl set to in seconds (Ex. 900): ")
    container.make_public(ttl=ttl)

    #create index file object
    index_content = get_str_input("Please enter a hello world message that will be present in your index: ")
    index = create_index(container, index_content)

    #select domain
    domain = select_domain_from_list(dns_client, "Please select the domain you wish to add the cname for this page to: ")
    cname_url = get_str_input("Please enter the subdomain you would like to point the cname to: ")
    fqdn = cname_url + "." + domain.name

    print "FQDN selected: " + fqdn

    cdn_uri = container.cdn_uri
    url = urlparse(cdn_uri).netloc

    #create cname to CDN url
    record = add_record(domain, fqdn, "CNAME", url)

    print record[0].name, " pointed to ", url

if __name__ == "__main__":
    main()
