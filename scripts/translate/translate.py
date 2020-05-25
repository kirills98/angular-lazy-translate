import argparse
import functools
import hashlib
import json
import os
import requests
import signal
import subprocess
import sys
import time

from deepmerge import always_merger


# SETTING SIG HANDLER

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# SHELL EXECUTOR

def shell(cmd: str, catch: bool = False) -> str:
    try:
        return subprocess.check_output(cmd, shell=True).decode("utf8")
    except Exception as e:
        if catch:
            return None
        raise e


# VARIABLES

JSON_DUMP_ARGS = {
    'indent': 2,
    'sort_keys': True,
    'ensure_ascii': False
}

DEFAULT_POEDITOR_API_URL = 'https://api.poeditor.com/v2'
DEFAULT_MAIN_TAG = 'master'
DEFAULT_UPLOAD_THROTTLE_SEC = 30

ENV_VAR_POEDITOR_ID = 'POEDITOR_ID'
ENV_VAR_POEDITOR_TOKEN = 'POEDITOR_TOKEN'
ENV_POEDITOR_ID = os.environ.get(ENV_VAR_POEDITOR_ID)
ENV_POEDITOR_TOKEN = os.environ.get(ENV_VAR_POEDITOR_TOKEN)


# SETTING ARGS PARSER

parser = argparse.ArgumentParser()
parser.add_argument(
    '--lang', '-l',
    help='Working languages [multiple]',
    required=True,
    action='append',
    dest='langs'
)
parser.add_argument(
    '--i18n-dir', '-d',
    help='Directory with i18n JSON files',
    action='store',
    dest='i18n_dir'
)


subparsers = parser.add_subparsers(help='actions', dest='action')

join_parser = subparsers.add_parser(
    'join',
    help='Join all chunks to one file'
)
join_parser.add_argument(
    '--file', '-f',
    help='Destination file to join [multiple] (if not present then print to stdout else should match to LANGS argument)',
    action='append',
    dest='files'
)


split_parser = subparsers.add_parser(
    'split',
    help='Split file to chunks'
)
split_input_group = split_parser.add_mutually_exclusive_group(required=True)
split_input_group.add_argument(
    '--file', '-f',
    help='Source file to split [multiple] (should match to LANGS argument)',
    action='append',
    dest='files'
)
split_input_group.add_argument(
    '--string', '-s',
    help='Input JSON string (if present multiple languages it should be JSON array)',
    action='store',
    dest='string'
)


hash_parser = subparsers.add_parser(
    'hash',
    help='Calc hash sum for translates to stdout'
)


def add_api_arguments(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        '--api-token', '-t',
        help='POEditor api token (default use environment variable "%s")' % ENV_VAR_POEDITOR_TOKEN,
        action='store',
        default=ENV_POEDITOR_TOKEN,
        dest='api_token'
    )
    p.add_argument(
        '--api-id', '-i',
        help='POEditor api ID (default use environment variable "%s")' % ENV_VAR_POEDITOR_ID,
        action='store',
        default=ENV_POEDITOR_ID,
        dest='api_id'
    )
    p.add_argument(
        '--api-url',
        help='POEditor api URL (default "%s")' % DEFAULT_POEDITOR_API_URL,
        action='store',
        default=DEFAULT_POEDITOR_API_URL,
        dest='api_url'
    )
    p.add_argument(
        '--tag', '-T',
        help='POEditor translation tag (default use current git branch)',
        action='store',
        dest='tag'
    )
    p.add_argument(
        '--main-tag',
        help='POEditor translation main tag (translations of this tag will merged with this current tag (argument --tag)) (default "%s")' % DEFAULT_MAIN_TAG,
        default=DEFAULT_MAIN_TAG,
        action='store',
        dest='main_tag'
    )


download_parser = subparsers.add_parser(
    'download',
    help='Download JSON from POEditor'
)
add_api_arguments(download_parser)
download_parser.add_argument(
    '--no-write', '-W',
    help='Don\'t write JSON to i18n files. JSON will write to stdout',
    action='store_false',
    default=True,
    dest='write'
)
download_parser.add_argument(
    '--file', '-f',
    help='Destination file to download [multiple] (if not preset will use --i18n-dir, ignore if --no-write, should match to LANGS argument)',
    action='append',
    dest='files'
)


upload_parser = subparsers.add_parser(
    'upload',
    help='Upload translates to POEditor'
)
add_api_arguments(upload_parser)
upload_parser.add_argument(
    '--file', '-f',
    help='Source file to upload [multiple] (if not preset will use --i18n-dir, should match to LANGS argument)',
    action='append',
    dest='files'
)
upload_parser.add_argument(
    '--throttle',
    help='Throttle time between upload languages (seconds) (default "%s")' % DEFAULT_UPLOAD_THROTTLE_SEC,
    action='store',
    default=DEFAULT_UPLOAD_THROTTLE_SEC,
    dest='throttle'
)


# PARSE ARGS

ARGS = parser.parse_args()


# UTILS

def get_current_branch() -> str:
    branch = shell('git rev-parse --abbrev-ref HEAD', True)

    if branch:
        return branch.split('\n')[0]

    return None


def read_json(file: str) -> dict:
    with open(file, encoding='utf-8') as json_file:
        return json.load(json_file)


def write_json(file: str, data: dict) -> None:
    with open(file, 'w', encoding='utf-8') as json_file:
        json.dump(data, json_file, **JSON_DUMP_ARGS)


def get_i18n_file(lang: str, path: str) -> str:
    return os.path.join(ARGS.i18n_dir, path, '%s.json' % lang)


def read_i18n_json(lang: str, path: str = '') -> dict:
    file = get_i18n_file(lang, path)
    if not os.path.isfile(file):
        return {}

    return read_json(file)


def write_i18n_json(lang, data: dict, path: str = '') -> None:
    write_json(get_i18n_file(lang, path), data)


def get_i18n_dir_list() -> list:
    return [x for x in os.listdir(ARGS.i18n_dir) if os.path.isdir(os.path.join(ARGS.i18n_dir, x))]


def get_from_json(content: dict, key: str) -> dict:
    path = key.split('.')
    try:
        return functools.reduce(lambda res, key: res.get(key), path, content)
    except:
        return None


def set_to_json(content: dict, key: str, value) -> None:
    path = key.split('.')
    obj = content
    key = path[-1]

    if len(path) > 1:
        for p in path[:-1]:
            if (p not in obj) or not isinstance(obj[p], dict):
                obj[p] = {}

            obj = obj[p]

    if not obj is None:
        obj[key] = value


def remove_from_json(content: dict, key: str) -> None:
    path = key.split('.')
    obj = content
    key = path[-1]

    if len(path) > 1:
        obj = get_from_json(content, '.'.join(path[:-1]))

    if (not obj is None) and (key in obj):
        del obj[key]


def read_joined_i18n_json(lang: str) -> dict:
    data = read_i18n_json(lang)
    dirs = get_i18n_dir_list()
    dirs.sort(key=len)

    for d in dirs:
        file_data = read_i18n_json(lang, d)
        merge_data = get_from_json(file_data, d)

        if not merge_data is None:
            set_to_json(data, d, merge_data)

    return data


def write_sliced_i18n_json(lang: str, data: dict) -> None:
    dirs = get_i18n_dir_list()
    dirs.sort(key=len, reverse=True)

    for d in dirs:
        value = get_from_json(data, d)

        if not value:
            value = {}

        chunk = {}
        set_to_json(chunk, d, value)
        remove_from_json(data, d)
        write_i18n_json(lang, chunk, d)

    write_i18n_json(lang, data)


def init_api_args(args) -> None:
    if (not args.api_id):
        raise Exception(
            'You should set argument --api-id or environment variable POEDITOR_ID')

    if (not args.api_token):
        raise Exception(
            'You should set argument --api-token or environment variable POEDITOR_TOKEN')

    if args.files and (len(args.files) != len(args.langs)):
        raise Exception('FILES should match LANGS')

    if (not args.tag):
        args.tag = get_current_branch()

        if (not args.tag):
            raise Exception(
                'You should set argument --tag or execute script from git repository')


def dump_json_output(data: list) -> str:
    return json.dumps(data if len(data) > 1 else data[0], **JSON_DUMP_ARGS)


def request_export_url(lang: str, **kwargs) -> str:
    r = requests.post(
        '%s/%s' % (kwargs['api_url'], 'projects/export'),
        data={
            'type': 'key_value_json',
            'api_token': kwargs['api_token'],
            'id': kwargs['api_id'],
            'language': lang,
            'tags': kwargs['tag']
        }
    )
    r.raise_for_status()

    return r.json()['result']['url']


def request_export(lang: str, **kwargs) -> dict:
    url = request_export_url(lang, **kwargs)
    r = requests.get(url)
    r.raise_for_status()

    try:
        return r.json()
    except:
        return {}


def request_upload(lang: str, data: dict, **kwargs) -> dict:
    is_main = kwargs['tag'] == kwargs['main_tag']
    tags = {
        'all': kwargs['main_tag'],
        'new': 'new-strings',
        'obsolete': 'deleted-strings',
        'overwritten_translations': 'changed-strings'
    } if is_main else {
        'new': ['new-strings', kwargs['tag']],
        'overwritten_translations': kwargs['tag']
    }

    r = requests.post(
        '%s/%s' % (kwargs['api_url'], 'projects/upload'),
        data={
            'api_token': kwargs['api_token'],
            'id': kwargs['api_id'],
            'language': lang,
            'updating': 'terms_translations',
            'overwrite': 1,
            'fuzzy_trigger': 1 if is_main else 0,
            'tags': json.dumps(tags, **JSON_DUMP_ARGS)
        },
        files={
            'file': ('%s.json' % lang, json.dumps(data, **JSON_DUMP_ARGS))
        }
    )

    r.raise_for_status()

    return r.json()


# ACTIONS

def action_split(args):
    data = []

    if args.string:
        string = json.loads(args.string)
        data = string if isinstance(string, list) else [string]
    else:
        data = list(map(lambda file: read_json(file), args.files))

    if len(data) != len(args.langs):
        raise Exception('FILES or STRING should match LANGS')

    for i, lang in enumerate(args.langs):
        write_sliced_i18n_json(lang, data[i])


def action_join(args):
    if args.files and (len(args.files) != len(args.langs)):
        raise Exception('FILES should match LANGS')

    result = []

    for i, lang in enumerate(args.langs):
        content = read_joined_i18n_json(lang)
        result.append(content)

        if args.files:
            write_json(os.path.abspath(args.files[i]), content)

    if not args.files:
        return dump_json_output(result)


def action_hash(args):
    result = ''

    for lang in args.langs:
        data = read_joined_i18n_json(lang)
        result += json.dumps(data, **JSON_DUMP_ARGS)

    return hashlib.md5(result.encode()).hexdigest()


def action_download(args):
    init_api_args(args)

    result = []

    for i, lang in enumerate(args.langs):
        # load all translates
        data = request_export(lang, **{**vars(args), **{'tag': None}})
        # load master translates
        data_master = request_export(
            lang, **{**vars(args), **{'tag': args.main_tag}}
        )
        # load tag translates if need
        data_tag = {}
        if args.tag != args.main_tag:
            data_tag = request_export(lang, **vars(args))

        data = always_merger.merge(data, data_master)
        data = always_merger.merge(data, data_tag)

        result.append(data)

        if args.write:
            if args.files:
                write_json(args.files[i], data)
            else:
                write_sliced_i18n_json(lang, data)

    if not args.write:
        return dump_json_output(result)


def action_upload(args):
    init_api_args(args)

    result = []

    for i, lang in enumerate(args.langs):
        if (i > 0):
            # required api throttle
            # https://poeditor.com/docs/api#projects_upload
            time.sleep(args.throttle)

        data = {}
        if args.files:
            data = read_json(args.files[i])
        else:
            data = read_joined_i18n_json(lang)

        r = request_upload(lang, data=data, **vars(args))
        result.append(r)

    return dump_json_output(result)


# DEFINE ACTION HANDLERS
ACTIONS = {
    'split': action_split,
    'join': action_join,
    'hash': action_hash,
    'download': action_download,
    'upload': action_upload,
}


# EXECUTE ACTION

result = ACTIONS[ARGS.action](ARGS)

if (result):
    print(result)
