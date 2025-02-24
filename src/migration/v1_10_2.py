import logging
from conf import DEFAULT_LOGGER
from pymongo import UpdateOne, DeleteOne
from lib import MongoCustomClient
from lib.util import print_log

_LOGGER = logging.getLogger(DEFAULT_LOGGER)


@print_log
def inventory_cloud_service_tags_refactoring(mongo_client: MongoCustomClient):
    items = mongo_client.find('INVENTORY', 'cloud_service', {}, {'provider': 1, 'tags': 1})
    operations = []
    for item in items:
        provider = item.get('provider', '')
        if isinstance(item['tags'], list):
            operations.append(
                UpdateOne({'_id': item['_id']},
                          {"$set": {"tags": _change_tags_to_list_of_dict(_change_tags(item['tags']), provider)}})
            )
        elif isinstance(item['tags'], dict):
            operations.append(
                UpdateOne({'_id': item['_id']},
                          {"$set": {"tags": _change_tags_to_list_of_dict(item['tags'], provider)}})
            )

    mongo_client.bulk_write('INVENTORY', 'cloud_service', operations)


@print_log
def inventory_cloud_service_delete_vm_instance_with_specific_plugin_id(mongo_client: MongoCustomClient):
    provider = "azure"
    cloud_service_type = "VirtualMachine"
    cloud_service_group = "Compute"
    mongo_client.delete_many('INVENTORY', 'cloud_service', {"provider": provider,
                                                            "cloud_service_group": cloud_service_group,
                                                            "cloud_service_type": cloud_service_type})


@print_log
def identity_service_account_set_additional_fields(mongo_client: MongoCustomClient):
    mongo_client.update_many('IDENTITY', 'service_account', {"service_account_type": {"$ne": "TRUSTED"}},
                             {"$set": {'service_account_type': 'GENERAL', 'scope': 'PROJECT'}}, upsert=True)


@print_log
def identity_provider_delete_providers(mongo_client: MongoCustomClient):
    mongo_client.delete_many('IDENTITY', 'provider', {"provider": "aws"})
    mongo_client.delete_many('IDENTITY', 'provider', {"provider": "google_cloud"})
    mongo_client.delete_many('IDENTITY', 'provider', {"provider": "aws"})


@print_log
def file_manager_file_delete_all_files(mongo_client: MongoCustomClient):
    mongo_client.delete_many('FILE_MANAGER', 'file', {})


@print_log
def inventory_record_delete_wrong_records(mongo_client: MongoCustomClient):
    cloud_service_ids = []
    items = mongo_client.find('INVENTORY', 'cloud_service',
                              {'provider': 'aws', 'cloud_service_group': 'IAM', 'cloud_service_type': 'Policy'},
                              {'cloud_service_id': 1})
    for item in items:
        cloud_service_ids.append(item['cloud_service_id'])

    items = mongo_client.find('INVENTORY', 'cloud_service',
                              {'provider': 'aws', 'cloud_service_group': 'IAM', 'cloud_service_type': 'Group'},
                              {'cloud_service_id': 1})
    for item in items:
        cloud_service_ids.append(item['cloud_service_id'])

    items = mongo_client.find('INVENTORY', 'cloud_service',
                              {'provider': 'aws', 'cloud_service_group': 'EKS', 'cloud_service_type': 'Cluster'},
                              {'cloud_service_id': 1})
    for item in items:
        cloud_service_ids.append(item['cloud_service_id'])

    items = mongo_client.find('INVENTORY', 'cloud_service',
                              {'provider': 'aws', 'cloud_service_group': 'EKS', 'cloud_service_type': 'NodeGroup'},
                              {'cloud_service_id': 1})
    for item in items:
        cloud_service_ids.append(item['cloud_service_id'])

    items = mongo_client.find('INVENTORY', 'cloud_service',
                              {'provider': 'aws', 'cloud_service_group': 'DirectConnect',
                               'cloud_service_type': 'DirectConnectGateway'},
                              {'cloud_service_id': 1})
    for item in items:
        cloud_service_ids.append(item['cloud_service_id'])

    operations = []
    cloud_service_ids = list(set(cloud_service_ids))

    items = mongo_client.find('INVENTORY', 'record', {'cloud_service_id': {'$in': cloud_service_ids}}, {'_id': 1})
    for item in items:
        operations.append(
            DeleteOne({'_id': item['_id']})
        )

    mongo_client.bulk_write('INVENTORY', 'record', operations)


def _change_tags(data):
    """ convert tags type ( list of dict -> dict )
    [AS-IS]
            1) general type >>> {"tags": [{key: 'type', value: 'test'}, {key: 'user', value: 'developer'}]}
            2) empty list   >>> {"tags": []}
            3) dict type    >>> {"tags":{"type":"test"}}
    [TO-BE]
            1) general type >>>  {"tags": {'type':'test', 'user':'developer'}}
            2) empty list   >>>  {"tags":{}}
            3) dict type    >>> {"tags":{"type":"test"}}
    """
    new_dict = {}
    if not len(data):
        return new_dict
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        for index in range(len(data)):
            new_dict[data[index]["key"]] = data[index].get("value", "")
    return new_dict


def _change_tags_to_list_of_dict(dict_values: dict, provider: str) -> list:
    tags = []
    for key, value in dict_values.items():
        new_tag = {
            'key': key,
            'value': value,
            'type': 'MANAGED',
            'provider': provider
        }
        tags.append(new_tag)
    return tags


def main(file_path):
    mongo_client: MongoCustomClient = MongoCustomClient(file_path, 'v1.10.2')
    inventory_cloud_service_tags_refactoring(mongo_client)
    inventory_cloud_service_delete_vm_instance_with_specific_plugin_id(mongo_client)
    identity_service_account_set_additional_fields(mongo_client)
    file_manager_file_delete_all_files(mongo_client)
    inventory_record_delete_wrong_records(mongo_client)
