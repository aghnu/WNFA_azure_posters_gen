import logging
from azure.storage.fileshare import ShareClient
from wnfapostersgen.secrets import connection_string

share = ShareClient.from_connection_string(conn_str=connection_string, share_name="assets")

def list_all_files(path):
    dir_client = share.get_directory_client(path)
    return list(dir_client.list_directories_and_files())

def get_file_binary(path):
    file_client = share.get_file_client(path)
    return file_client.download_file().readall()    