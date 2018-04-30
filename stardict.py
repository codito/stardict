#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""Stardict can parse and query stardict dictionary files.

 _______ _________ _______  _______  ______  _________ _______ _________
(  ____ \\__   __/(  ___  )(  ____ )(  __  \ \__   __/(  ____ \\__   __/
| (    \/   ) (   | (   ) || (    )|| (  \  )   ) (   | (    \/   ) (
| (_____    | |   | (___) || (____)|| |   ) |   | |   | |         | |
(_____  )   | |   |  ___  ||     __)| |   | |   | |   | |         | |
      ) |   | |   | (   ) || (\ (   | |   ) |   | |   | |         | |
/\____) |   | |   | )   ( || ) \ \__| (__/  )___) (___| (____/\   | |
\_______)   )_(   |/     \||/   \__/(______/ \_______/(_______/   )_(

"""
import logging
import os
from collections import namedtuple
from struct import unpack

import click
import idzip

logger = logging.getLogger("stardict")

Configuration = namedtuple("Configuration", "ifo_path idx_path syn_path"
                           " dict_path")
IFO = namedtuple("IFO", "version")


def parse_ifo(config):
    """Parse an ifo file.

    Specification of IFO file is available at:
    https://github.com/huzheng001/stardict-3/blob/master/dict/doc/StarDictFileFormat
    Note that we're not validating the contents strictly.

    Args:
        config (Configuration): Configuration for stardict

    Returns:
        return dictionary of entries in IFO file

    # Validation
    # version: must be "2.4.2" or "3.0.0".
    # Since "3.0.0", StarDict accepts the "idxoffsetbits" option.

    # Available options:
    # bookname=      // required
    # wordcount=     // required
    # synwordcount=  // required if ".syn" file exists.
    # idxfilesize=   // required
    # idxoffsetbits= // New in 3.0.0
    # author=
    # email=
    # website=
    # description=	// You can use <br> for new line.
    # date=
    # sametypesequence= // very important.
    # dicttype=

    """
    if not os.path.exists(config.ifo_path):
        logger.info("IFO file doesn't exist at '{}'".format(config.ifo_path))
        return {}

    magic_header = "StarDict's dict ifo file"
    with open(config.ifo_path, "r", encoding="utf-8") as f:
        magic_string = f.readline().rstrip()
        if (magic_string != magic_header):
            logger.info("IFO: Incorrect header: {}".format(magic_string))
            return {}

        options = (l.split("=") for l in map(str.rstrip, f) if l is not "")
        return {k.strip(): v.strip() for k, v in options}


def parse_idx(config):
    r"""Parse an IDX file.

    Args:
        config (Configuration): a configuration object

    Returns:
        an iterable list of words.

    The word list is a sorted list of word entries.

    Each entry in the word list contains three fields, one after the other:
         word_str;  // a utf-8 string terminated by '\0'.
         word_data_offset;  // word data's offset in .dict file
         word_data_size;  // word data's total size in .dict file

    """
    word_idx = {}
    if not os.path.exists(config.idx_path):
        return word_idx

    with open(config.idx_path, "rb") as f:
        def read_word(f):
            word = bytearray()
            c = f.read(1)
            while c and c != b'\0':
                word.extend(c)
                c = f.read(1)
            return word.decode("utf-8")

        while True:
            word_str = read_word(f)
            # TODO support 64bit offset in stardict v3.0.0
            offset_size = 8

            word_pointer = f.read(offset_size)
            if not word_pointer:
                break
            word_idx[word_str] = unpack(">II", word_pointer)
    return word_idx


def parse_dict(config, word, offset, size):
    """Parse a dictionary file.

    Args:
        config (Configuration): stardict configuration
        word (str): word to lookup in the dictionary
        offset (int): offset of the definition in dict file
        size (int): size of the definition data

    Returns:
        definition of a word in the dictionary

    """
    definition = None
    if not os.path.exists(config.dict_path):
        logger.info("dict file not found: {}".format(config.dict_path))
        return definition

    # TODO
    # support sametypesequence
    open_dict = open
    if config.dict_path.endswith(".dz"):
        open_dict = idzip.open

    with open_dict(config.dict_path, "rb") as f:
        f.seek(offset)
        data = f.read(size)
        return data


def parse_syn(config, word):
    r"""Parse a syn file with synonyms.

    Args:
        config (Configuration): stardict configuration
        word (str): synonym word for lookup

    Returns:
        index of the actual word for a given synonym in idx file

    The format is simple. Each item contain one string and a number.
    synonym_word;  // a utf-8 string terminated by '\0'.
    original_word_index; // original word's index in .idx file.
    Then other items without separation.
    When you input synonym_word, StarDict will search original_word;

    The length of "synonym_word" should be less than 256. In other
    words, (strlen(word) < 256).
    original_word_index is a 32-bits unsigned number in network byte order.
    Two or more items may have the same "synonym_word" with different
    original_word_index.

    """
    return None


@click.command()
@click.argument("dict_path", type=click.Path(exists=True))
@click.argument("word", type=str)
@click.option("--debug", is_flag=True, show_default=True,
              help="Show diagnostic messages.")
def start(dict_path, word, debug):
    """Stardict can parse and query stardict dictionary files."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logger.info("Verbose messages are enabled.")


if __name__ == '__main__':
    start()
