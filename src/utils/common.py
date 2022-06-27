import logging
import json
import os
from shutil import rmtree

from subprocess import run
from pathlib import Path
from typing import Iterable

FILEBROWSER_PATH = Path(os.path.join(os.path.dirname(__file__), "..", "utils", "filebrowser.exe")).__str__()

def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger
    :return:
    """
    try:
        logger = logger
    except:
        logger = logging.getLogger(name)
    finally:
        logger.setLevel(logging.INFO)

        # create file handler which logs even debug messages
        # fh = logging.FileHandler(logfile, mode='w')
        # fh.setLevel(logging.DEBUG)
        # create console handler with a higher log level

        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        # create formatter and add it to the handlers
        formatter = logging.Formatter('%(levelname)s | %(filename)s %(lineno)d %(funcName)s | %(message)s')
        # fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # Remove handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        logger.addHandler(ch)

        return logger

def read_json(p: str) -> dict:
    """
    Read a json file and return a dictionary
    :param p: path to file
    :return:
    """
    with open(p) as json_file:
        return json.load(json_file)


def open_folder(path):
    """
    Open a file explorer to a path
    :param path: path to folder
    :return:
    """
    path = os.path.normpath(path)

    if os.path.isdir(path):
        run([FILEBROWSER_PATH, path])


def get_files(path: str, extension: str = "") -> list:
    """
    Get all files in a directory
    :param path: path to directory
    :param extension: extension of files to get
    :return: list of files
    """
    files = list()
    for file in os.listdir(path):
        if extension in file:
            files.append(Path(os.path.join(path, file)))
    return files


def remove_file(path: str):
    """
    Remove a file
    """
    if os.path.isfile(path) or os.path.islink(path):
        os.remove(path)  # remove the file
    elif os.path.isdir(path):
        rmtree(path)  # remove dir and all contains
    else:
        raise ValueError("file {} is not a file or dir.".format(path))


def open_folder(path):
    """
    Open a file explorer to a path
    :param path: path to folder
    :return:
    """
    path = os.path.normpath(path)

    if os.path.isdir(path):
        run([FILEBROWSER_PATH, path])


def save_list(filepath: Path, lines: list):
    """
    Save a list to a file
    :param filepath: path to file
    :param lines: list of lines
    :return:
    """

    # Flatten umap objects
    lines = list(flatten_list(lines))

    # Remove Duplicates
    lines = list(dict.fromkeys(lines))

    with open(filepath.__str__(), 'w') as f:
        f.write('\n'.join(lines))
    return filepath.__str__()


def save_json(p: str, d):
    """
    Save a dictionary to a json file
    :param p: path to file
    :param d: dictionary
    :return:
    """
    with open(p, 'w') as jsonfile:
        json.dump(d, jsonfile, indent=4)


def read_json(p: str) -> dict:
    """
    Read a json file and return a dictionary
    :param p: path to file
    :return:
    """
    with open(p) as json_file:
        return json.load(json_file)

def read_files(p:str) -> dict:
    # read all json files in a folder and make them in to a dict
    files = get_files(p, ".json")
    d = {}
    for f in files:
        d[f.stem] = read_json(f)
    return d
    


def shorten_path(file_path, length) -> str:
    """
    Shorten a path to a given length
    :param file_path: path to shorten
    :param length: length to shorten to
    :return: shortened path
    """
    return f"..\{os.sep.join(file_path.split(os.sep)[-length:])}"


def flatten_list(collection):
    """
    Flatten a list of lists
    :param collection: list of lists
    :return: list
    """

    for x in collection:
        if isinstance(x, Iterable) and not isinstance(x, str):
            yield from flatten_list(x)
        else:
            yield x


