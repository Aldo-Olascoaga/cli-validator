import importlib.util
import json
import logging
import os
import shutil
from json import JSONDecodeError
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobClient


BLOB_URL = 'https://azcmdchangemgmt.blob.core.windows.net'
CONTAINER_NAME = 'cmd-metadata-per-version'

logger = logging.getLogger(__name__)


class ResourceNotExistException(Exception):
    """
    The metadata file does not exist for specific version.
    """
    def __init__(self, msg, *args) -> None:
        self.msg = msg
        super().__init__(msg, *args)


def download_blob(url: str, target_path: str):
    try:
        blob = BlobClient.from_blob_url(url)
        with open(target_path, "wb") as f:
            blob = blob.download_blob()
            blob.readinto(f)
    except ResourceNotFoundError as e:
        raise ResourceNotExistException(e.message)


def fetch_metas(version: str, target_dir: str = './cmd_meta'):
    """
    Fetch `cmd-metadata-per-version` from Azure Blob
    :param version: version num of `azure-cli`
    :param target_dir: root directory to store downloaded data
    """
    if not os.path.exists(f'{target_dir}/azure-cli-{version}'):
        os.makedirs(f'{target_dir}/azure-cli-{version}')
    download_blob(f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/index.txt',
                  f'{target_dir}/azure-cli-{version}/index.txt')
    with open(f'{target_dir}/azure-cli-{version}/index.txt', 'r', encoding='utf-8') as f:
        for file_name in f.readlines():
            file_name = file_name.strip(' \n')
            try:
                download_blob(f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/{file_name}',
                              f'{target_dir}/azure-cli-{version}/{file_name}')
            except ResourceNotExistException as e:
                logger.error(f'`azure-cli-{version}/{file_name}` not Found', e)


def load_metas_from_disk(version: str, meta_dir: str = './cmd_meta'):
    """
    Load Command Metadata from local disk
    :param version: version number of `azure-cli`
    :param meta_dir: root directory to store dumped data
    :return: list of command metadata
    """
    if not os.path.exists(f'{meta_dir}/azure-cli-{version}/index.txt'):
        return None
    metas = {}
    with open(f'{meta_dir}/azure-cli-{version}/index.txt', 'r', encoding='utf-8') as f:
        for file_name in f.readlines():
            file_name = file_name.strip(' \n')
            try:
                with open(f'{meta_dir}/azure-cli-{version}/{file_name}', 'r', encoding='utf-8') as meta_f:
                    metas[file_name] = json.load(meta_f)
            except (FileNotFoundError, JSONDecodeError) as e:
                logger.error(f'Loading meta data in {file_name} failed: {e}')
    return metas


def load_metas(version: str, meta_dir: str = './cmd_meta'):
    """
    Load Command Metadata from local cache, fetch from Blob if not found
    :param version: version of `azure-cli` to be loaded
    :param meta_dir: root directory to cache Command Metadata
    :return: list of command metadata
    """
    metas = load_metas_from_disk(version, meta_dir)
    if not metas:
        if importlib.util.find_spec('aiohttp') is not None:
            import asyncio
            from .aio import fetch_metas as aio_fetch_metas
            asyncio.run(aio_fetch_metas(version, meta_dir))
        else:
            logger.info('Module \'aiohttp\' is not installed. Downloading metadata sequentially now.')
            fetch_metas(version, meta_dir)
        metas = load_metas_from_disk(version, meta_dir)
    return metas


def fetch_meta(version: str, module: str, target_dir: str = './cmd_meta'):
    if not os.path.exists(f'{target_dir}/azure-cli-{version}'):
        os.makedirs(f'{target_dir}/azure-cli-{version}')
    file_name = f'az_{module}_meta.json'
    try:
        download_blob(f'{BLOB_URL}/{CONTAINER_NAME}/azure-cli-{version}/{file_name}',
                      f'{target_dir}/azure-cli-{version}/{file_name}')
    except ResourceNotExistException as e:
        logger.error(f'`azure-cli-{version}/{file_name}` not Found', e)


def load_meta_from_disk(version: str, module: str, meta_dir: str = './cmd_meta'):
    file_name = f'az_{module}_meta.json'
    try:
        with open(f'{meta_dir}/azure-cli-{version}/{file_name}', 'r', encoding='utf-8') as meta_f:
            return json.load(meta_f)
    except (FileNotFoundError, JSONDecodeError) as e:
        logger.error(f'Loading meta data in {file_name} failed: {e}')
    return None


def load_meta(version: str, module: str, meta_dir: str = './cmd_meta'):
    meta = load_meta_from_disk(version, module, meta_dir)
    if not meta:
        fetch_meta(version, module, meta_dir)
        meta = load_meta_from_disk(version, module, meta_dir)
    return meta


def clear(version: Optional[str], meta_dir: str = './cmd_meta'):
    """
    Clear the directory of downloaded data
    :param version: clear data of specific version, all data if None
    :param meta_dir: root directory to store downloaded data
    """
    if version:
        if os.path.exists(f'{meta_dir}/azure-cli-{version}'):
            shutil.rmtree(f'{meta_dir}/azure-cli-{version}')
    else:
        if os.path.exists(meta_dir):
            shutil.rmtree(meta_dir)


def _attach_sub_group_to_node(sub_group, tree_node, module):
    for name, command in sub_group["commands"].items():
        tree_node[name.split()[-1]] = module
    for name, sub_group in sub_group["sub_groups"].items():
        name = name.split()[-1]
        if name not in tree_node:
            tree_node[name] = {}
        next_tree_node = tree_node[name]
        _attach_sub_group_to_node(sub_group, next_tree_node, module)


def build_command_tree(metas):
    tree = {}
    for meta in metas.values():
        module = meta["module_name"]
        _attach_sub_group_to_node(meta, tree, module)
    return tree
