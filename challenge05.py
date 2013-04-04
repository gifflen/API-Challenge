"""
Write a script that creates a Cloud Database instance. This instance should contain at least one database,
and the database should have at least one user that can connect to it.
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


def get_storage_size():
    MIN = 1
    MAX = 50
    size = get_int_input("Please enter the storage size in GB " + str(MIN) + "-" + str(MAX) + ": ")
    if 50 < size or size < 1:
        print "Invalid storage size selected"
        get_storage_size()
    return size


def select_flavor_from_list(db_client, message="Please select a flavor by number: "):
    """
    Offers the user a list of flavors to select from based on the passed client
    :param db_client: A pyrax cloud db client object with its auth already initialized.
    :return: A flavor object based on the selection
    """
    flavors = db_client.list_flavors()
    for num in range(len(flavors)):
        print num, ") Flavor: ", flavors[num].name

    choice = get_int_input(message)
    flavor = None
    if 0 <= choice <= len(flavors) - 1:
        flavor = flavors[choice]
    else:
        print "Invalid Choice."
        select_flavor_from_list(db_client)
    return flavor


def create_instance(db_client, instance_name, flavor, volume):
    instance = db_client.create(instance_name, flavor=flavor, volume=volume)
    return instance


def create_db(db_instance, db_name):
    db = db_instance.create_database(db_name)
    return db


def create_db_user(db_instance, username, password, database_list):
    user = db_instance.create_user(name=username, password=password, database_names=database_list)
    return user


def print_user_info(user):
    print "Username: " + user.name
    for db in user.databases:
        print "DB: " + db['name']


def main():
    auth()

    db_client = pyrax.cloud_databases

    flavor = select_flavor_from_list(db_client, "Please select a database flavor: ")
    print "You have selected: " + flavor.name

    db_instance = get_str_input("Please enter a Instance name: ")
    db_name = get_str_input("Please enter the DB name: ")
    db_username = get_str_input("Please enter the DB user name: ")
    db_password = get_str_input("Please enter the DB user password: ")

    size = get_storage_size()

    instance = create_instance(db_client, instance_name=db_instance, flavor=flavor, volume=size)
    print "Waiting for instance to be created."
    if not pyrax.utils.wait_until(instance, 'status', 'ACTIVE', interval=30, verbose=True):
        print "Creating the instance failed"
        quit()
    print instance.name, " instance created. ID: ", instance.id

    db = create_db(instance, db_name)
    print db.name, "created"

    user = create_db_user(instance, db_username, db_password, [db])
    print "User created:"
    print_user_info(user)


if __name__ == "__main__":
    main()

