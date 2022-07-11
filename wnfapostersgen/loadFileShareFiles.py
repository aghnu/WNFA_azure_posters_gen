from azure.storage.fileshare import ShareClient
from wnfapostersgen.secrets import connection_string
from azure.storage.fileshare.aio import ShareClient as ShareClientAsync

import asyncio

share = ShareClient.from_connection_string(conn_str=connection_string, share_name="assets")

def list_all_files(path):
    dir_client = share.get_directory_client(path)
    return list(dir_client.list_directories_and_files())

def get_file_binary(path):
    file_client = share.get_file_client(path)
    return file_client.download_file().readall()    





async def get_data_from_fileclient(file_client):
    data = await file_client.download_file()
    return await data.readall()


async def get_list_of_files_binary_async(a_list_path):
    
    # client
    client = ShareClient.from_connection_string(conn_str=connection_string, share_name="assets")

    # download files
    tasks = []
    for path in a_list_path:
        file_client = client.get_file_client(path)
        task = asyncio.create_task(get_data_from_fileclient(file_client))
        tasks.append(task)
    
    # get binary
    files_binary = []
    for task in tasks:
        files_binary.append(await task)
    
    # close client
    await client.close()

    return files_binary