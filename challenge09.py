"""
Write an application that when passed the arguments FQDN, image,
and flavor it creates a server of the specified image and flavor with the same name as the fqdn,
and creates a DNS entry for the fqdn pointing to the server's public IP.
"""
from __future__ import with_statement
from urlparse import urlparse
import pyrax
import os
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


def get_domain_parts(url, tlds):
    urlElements = urlparse(url).hostname.split('.')
    # urlElements = ["abcde","co","uk"]
    for i in range(-len(urlElements),0):
        lastIElements = urlElements[i:]
        #    i=-3: ["abcde","co","uk"]
        #    i=-2: ["co","uk"]
        #    i=-1: ["uk"] etc

        candidate = ".".join(lastIElements) # abcde.co.uk, co.uk, uk
        wildcardCandidate = ".".join(["*"]+lastIElements[1:]) # *.co.uk, *.uk, *
        exceptionCandidate = "!"+candidate

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
    except (pyrax.exc.BadRequest, pyrax.exc.DomainRecordAdditionFailed) as e:
        raise

    return generated_record


def main():
    #TODO: argparse these
    FQDN = "testserver.brucestringer.com"
    flavor_id = "2"
    image_uuid = "c195ef3b-9195-4474-b6f7-16e5bd86acd0"

    auth()
    cs_client = pyrax.cloudservers
    dns_client = pyrax.cloud_dns

    # load tlds, ignore comments and empty lines:
    with open("tlds.txt") as tldFile:
        tlds = [line.strip() for line in tldFile if line[0] not in "/\n"]

    domain_parts = get_domain_parts("http://" + FQDN, tlds)
    print "Domain:", domain_parts.domain
    print "Subdomains:", domain_parts.subdomains or "None"
    print "TLD:", domain_parts.tld

    domain_name = domain_parts.domain + "." + domain_parts.tld

    #Find domain
    try:
        domain = dns_client.find(name=domain_name)
    except pyrax.exc.NotFound:
        print "There is no DNS information for the domain '%s'." % domain_name
        sys.exit(1)

    records = domain.list_records()
    for record in records:
        if record.name.lower() == FQDN.lower() and record.type in ['A', 'CNAME']:
            print "Record for this FQDN %s already exists. Exiting" % FQDN
            sys.exit(2)

    print "Creating server: ", FQDN
    server = cs_client.servers.create(FQDN, image_uuid, flavor_id)

    if pyrax.utils.wait_until(server, 'status', 'ACTIVE', verbose_atts=['progress'], interval=30, verbose=True) is None:
        print "Server failed to build in a timely manner."
        quit()

    #TODO format server info

    #Grab network
    server.get()
    ips = server.addresses['public']

    ip = [ip['addr'] for ip in ips if ip['version'] == 4][0]


    #create DNS entry based on fqdn
    record = add_record(domain, fqdn=FQDN, record_type="A", data=ip)
    print record

if __name__ == "__main__":
    main()
