import os
import sys
import time
import docker
import logging
import requests

from typing import Literal
from datetime import datetime
from itertools import repeat
from functools import partial
from docker.models.containers import Container

# Local imports
from utils.constants import *


LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    stream=sys.stdout,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=LOG_LEVEL)
LOG = logging.getLogger(__name__)

CONTAINER = None


def create_folder(path:str, folder:str):
    """
    Create a folder

    Args:
        path (str): Directory in which to create a folder
        folder (str): Name of folder to create
    """
    if folder not in os.listdir(path):
        os.mkdir(f"{path}{folder}")


def download(url:str, output_path:str, file_name:str, file_type:str) -> bool:
    """
    Download output from parser

    Args:
        url (str): URL to retrieve the parsed output
        output_path (str): Directory to store parsed files
        file_name (str): Name of file that was parsed
        file_type (str): Type of parsed output to download
    """
    r = requests.get(url)
    if not r.ok:
        LOG.error(f"Download failed || url: {url} || status_code: {r.status_code} || reason: {r.reason}")
        return False
    create_folder(path=output_path, folder=file_name)
    path = f"{output_path}{file_name}/{file_name}.{file_type}"
    with open(path, 'wb') as f:
        f.write(r.content)
        LOG.debug(f"File successfully downloaded and stored in {path}")
    return True


def download_files(
    file_id:str,
    output_path:str,
    file_name:str,
    json:bool=True,
    md:bool=True,
    text:bool=True,
    csv:bool=True
):
    """
    Download the parsed files

    Args:
        file_id (str): The file id provided by the parser
        output_path (str): Directory to store parsed files
        file_name (str): Name of file that was parsed
        json (bool): Flag to store json output
        md (bool): Flag to store md output
        text (bool): Flag to store text output
        csv (bool): Flag to store csv output
    """
    partial_downlaod = partial(download, output_path=output_path, file_name=file_name)
    file_url = f"/{file_id}?download=1"
    json_passed, md_passed, text_passed, csv_passed = repeat(False, 4)
    if json:
        json_passed = partial_downlaod(url=f"{JSON_URL}{file_url}", file_type='json')
    if md:
        md_passed = partial_downlaod(url=f"{MD_URL}{file_url}", file_type='md.zip')
    if text:
        text_passed = partial_downlaod(url=f"{TEXT_URL}{file_url}", file_type='txt')
    if csv:
        csv_passed = partial_downlaod(url=f"{CSV_URL}{file_url}", file_type='csv')
    
    if not json_passed and not md_passed and not text_passed and not csv_passed:
        parse_failed(output_path=output_path, file_name=file_name)


def find_container(image:str=IMAGE, log_error=True) -> Container | None:
    """
    Find the container if it is running

    Args:
        image (str): The image of the container. Defaults to "axarev/parsr"
        log_error (bool): Flag for logging error
    
    Returns:
        (Container) The running container
    """
    client = docker.from_env()
    for container in client.containers.list():
        if [image] == container.image.tags:
            return container
    error_msg = "Couldn't find relevant container || You may now... PANIC!!!!!!!!"
    if log_error:
        LOG.error(error_msg)
    raise(Exception(error_msg))


def parse_failed(output_path, file_name):
    # Uncomment this if you want the file to be skipped on the next run
    # create_folder(path=output_path, folder=file_name)
    # LOG.info(f"Created empty output folder so that the PDF will be skipped when reattemped || file {file_name}")
    LOG.warning(f"Failed to parse time due to timeout, moving on to the next || timeout: {seconds_to_time(DOCKER_TIMEOUT)} || file: {file_name}")


def parse_file(
    file_name:str,
    input_path:str,
    output_path:str,
    config_path,
    attempt:int=1
):
    """
    Parse a single file

    Args:
        file_name (str): Name of file, without file extension
        input_path (str): Complete path to file, including the file name and extension
        output_path (str): Directory to store parsed files
        config_path (str): Path of config file used by the parser
        attempt (int): Attempt counter, retry limit
    """
    file_id = send_to_parser(file_name=file_name, path=input_path, config_path=config_path)
    if wait_til_done(url=f"{STATUS_URL}/{file_id}"):
        download_files(file_id=file_id, file_name=file_name, output_path=output_path)
    else:
        if attempt < ATTEMPT_LIMIT:
            LOG.warning(f"Parser timed out {ATTEMPT_LIMIT} times || File: {file_name}")
            parse_file(
                file_name=file_name,
                input_path=input_path,
                output_path=output_path,
                config_path=config_path,
                attempt=attempt+1)
        else:
            parse_failed(output_path=output_path, file_name=file_name)
            return False
    return True
    

def parse_files(
    input_path:str,
    output_path:str,
    config_path:str,
    valid_file_ext:list[str]=['pdf']
):
    """
    Parse all files from the provided input directory

    Args:
        input_path (str): Directory containing files to be parsed
        output_path (str): Directory to store parsed files
        config_path (str): Path of config file used by the parser
        valid_file_ext (list[str]): List of valid file extensions. Defaults to ["pdf"]
    """
    output_folder = os.listdir(output_path)
    input_folder = os.listdir(input_path)
    for folder in filter(os.path.isdir, input_folder):
        parse_files(input_path=folder, output_path=output_folder, config_path=config_path)
    for i in input_folder:
        file_name, valid = validate_file(file=i, valid_file_ext=valid_file_ext, output_path=output_folder)
        if not valid:
            continue
        LOG.info(f"Parsing started: {i}")
        parsed = parse_file(
            file_name=file_name,
            input_path=f"{input_path}{i}",
            output_path=output_path,
            config_path=config_path)
        if parsed: LOG.info(f"Parsing completed: {i}")
    LOG.info(f"All files have been parsed || output folder: {output_path}")


def restart_parsr(image:str=IMAGE):
    """
    Restart the Parsr container

    Args:
        image (str): The image of the container. Defaults to "axerev/parsr"
    """
    LOG.info(f"Restarting {image}")
    if CONTAINER is not None:
        CONTAINER.restart()
    else:
        container = find_container(image)
        container.restart()
    # Give the container a few seconds to before moving on
    time.sleep(5)
    LOG.info(f"{image} was successfully restarted")


def run_parsr(**kwargs):
    """
    Run parser, with provided config

    Args:
        input_path (str): Directory containing files to be parsed
        output_path (str): Directory to store parsed files
        config_path (str): Path of config file used by the parser
        valid_file_ext (list[str]): List of valid file extensions. Defaults to ["pdf"]
    """
    try:
        start_parsr()
        parse_files(**kwargs)
        stop_parsr()
    except Exception as e:
        LOG.error(f"Fatal error, shutting down || error_message: {e}")
        stop_parsr()


def seconds_to_time(seconds:int) -> str:
    """
    Converts seconds to a human readable time format
    e.g. 7200s -> 02:00:00 (HH:MM:SS)

    Args:
        seconds (int): Seconds

    Returns:
        (str) Time format of the seconds
    """
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hour, minutes, seconds)


def send_to_parser(file_name:str, path:str, config_path:str) -> str:
    """
    Send file to the parser

    Args:
        file_name (str): Name of file, without file extension
        path (str): Complete path to file, including the file name and extension
        config_path (str): Path of config file used by the parser
    
    Returns:
        (str) The file id provided by Parsr
    """
    files = {
        'file': (file_name, open(path, 'rb'), 'application/pdf'),
        'config': ('config', open(config_path, 'rb'), 'application/json')
    }
    upload = requests.post(UPLOAD_URL, files=files)
    if not upload.ok:
        raise(Exception(upload.reason))

    return upload.text


def start_parsr(image:str=IMAGE):
    """
    Start the Parsr container

    Args:
        image (str): The image of the container. Defaults to "axarev/parsr"
    """
    global CONTAINER
    client = docker.from_env()
    CONTAINER = client.containers.run(image, detach=True, ports={3001: 3001})
    time.sleep(5)
    LOG.info(f"PDF parser server started || container: {image}")


def stop_parsr(image:str=IMAGE):
    """
    Stop the Parsr container

    Args:
        image (str): The image of the container. Defaults to "axarev/parsr"
    """
    LOG.info(f"Stopping {image}")
    if CONTAINER is not None:
        CONTAINER.stop()
    else:
        try:
            container = find_container(image, log_error=False)
            container.stop()
        except:
            LOG.info(f"{image} wasn't running")
            return
    LOG.info(f"{image} was successfully stopped")


def validate_file(
    file:str,
    output_path:str,
    valid_file_ext:list[str]=['pdf']
) -> tuple[None, Literal[False]] | tuple[str, Literal[True]]:
    """
    Validate that the input file is the correct format (path, not content)

    Args:
        file (str): The file name
        output_path (str): Output path
        valid_file_ext (list[str]): List of valid file extensions. Defaults to ["pdf"]
    """
    split = file.split('.', 1)
    file_name = split[0]
    file_ext = split[1]
    if file_ext.lower() not in valid_file_ext and file_ext.upper() not in valid_file_ext:
        LOG.warning(f"Invalid file extension || expected: {valid_file_ext} || received {file_ext}")
        return None, False
    if file_name in output_path:
        LOG.debug(f"Skipping as it is already parsed || {file}")
        return None, False
    return file_name, True


def wait_til_done(url:str) -> bool:
    """
    Wait for the document to finish parsing

    Args:
        url (str): Status url

    Returns:
        (bool) Succeded of failed
    """
    start = datetime.now()
    status = requests.get(url)
    while status.status_code != 201:
        if (datetime.now() - start).seconds > DOCKER_TIMEOUT:
            LOG.warning("Parser timed out || Restarting parsr container")
            restart_parsr(image='axarev/parsr:latest')
            return False
        time.sleep(5)
        status = requests.get(url)
    return True
