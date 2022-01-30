#!/usr/bin/env python3

import argparse
import dataclasses
import shlex
import json
import os
import re
import subprocess
import sys
import tempfile
import typing


def read_file_contents(path: str) -> str:
    with open(path, 'r') as ifile:
        return ifile.read()


@dataclasses.dataclass
class CCEntry:
    directory: str
    command: typing.List[str]
    file_path: str


@dataclasses.dataclass
class Include:
    include_line: str  # e.g. '#include <stdio.h>'
    orig_path: str  # e.g. 'stdio.h'
    real_path: str  # e.g. '/usr/include/stdio.h'


# Handle special symbols like quotes
def command_to_cmdline(command):
    s = shlex.shlex(command, posix=True)
    s.whitespace_split = True
    args = list(s)
    return args


def read_compile_commands(path: str) -> typing.Dict[str, CCEntry]:
    compile_commands_raw = read_file_contents(path)
    compile_commands_json = json.loads(compile_commands_raw)

    compile_commands = {
        entry['file']: CCEntry(
            directory=entry['directory'],
            command=command_to_cmdline(entry['command']),
            file_path=entry['file'],
        )
        for entry in compile_commands_json
    }
    return compile_commands


def adjust_cc_command(command: CCEntry) -> typing.List[str]:
    command_items = command.command

    # Read the code from stdin instead of <some>.cpp
    i = 0
    while i < len(command_items):
        item = command_items[i]

        if item == '-c':
            command_items = command_items[:i] + command_items[i + 2 :]
            break
        i += 1

    # Drop -o xxx
    i = 0
    while i < len(command_items):
        item = command_items[i]
        if item == '-o':
            command_items = command_items[:i] + command_items[i + 2 :]
            break
        i += 1

    command_items.append('-H')
    command_items.append('-E')
    return command_items


def is_include(string: str) -> bool:
    return bool(re.match(r'^\s*#include ', string))


def is_include_or_empty(string: str) -> bool:
    return is_include(string) or not string.strip()


def extract_file_relpath(line: str) -> str:
    res = re.match(r'^\s*#include\s*(\<[^>]*\>|\"[^"]*\")', line)
    if res:
        # "file.hpp" -> file.hpp
        value = res.group(1)[1:-1]
        return value

    raise Exception(f'Bad include format, I don\'t know to process it: {line}')


# Yeah, this is ugly to store the standard headers list, but it works
HEADERS_C = [
    #
    # C standard
    #
    'assert.h',
    'limits.h',
    'signal.h',
    'stdlib.h',
    'ctype.h',
    'locale.h',
    'stdarg.h',
    'string.h',
    'errno.h',
    'math.h',
    'stddef.h',
    'time.h',
    'float.h',
    'setjmp.h',
    'stdio.h',
    'iso646.h',
    'wchar.h',
    'wctype.h',
    'complex.h',
    'inttypes.h',
    'stdint.h',
    'tgmath.h',
    'fenv.h',
    'stdbool.h',
    'stdalign.h',
    'stdatomic.h',
    'stdnoreturn.h',
    'threads.h',
    'uchar.h',
    #
    # POSIX
    #
    'aio.h',
    'libgen.h',
    'spawn.h',
    'sys/time.h',
    'arpa/inet.h',
    'limits.h',
    'stdarg.h',
    'sys/times.h',
    'assert.h',
    'locale.h',
    'stdbool.h',
    'sys/types.h',
    'complex.h',
    'math.h',
    'stddef.h',
    'sys/uio.h',
    'cpio.h',
    'monetary.h',
    'stdint.h',
    'sys/un.h',
    'ctype.h',
    'mqueue.h',
    'stdio.h',
    'sys/utsname.h',
    'dirent.h',
    'ndbm.h',
    'stdlib.h',
    'sys/wait.h',
    'dlfcn.h',
    'net/if.h',
    'string.h',
    'syslog.h',
    'errno.h',
    'netdb.h',
    'strings.h',
    'tar.h',
    'fcntl.h',
    'netinet/in.h',
    'stropts.h',
    'termios.h',
    'fenv.h',
    'netinet/tcp.h',
    'sys/ipc.h',
    'tgmath.h',
    'float.h',
    'nl_types.h',
    'sys/mman.h',
    'time.h',
    'fmtmsg.h',
    'poll.h',
    'sys/msg.h',
    'trace.h',
    'fnmatch.h',
    'pthread.h',
    'sys/resource.h',
    'ulimit.h',
    'ftw.h',
    'pwd.h',
    'sys/select.h',
    'unistd.h',
    'glob.h',
    'regex.h',
    'sys/sem.h',
    'utime.h',
    'grp.h',
    'sched.h',
    'sys/shm.h',
    'utmpx.h',
    'iconv.h',
    'search.h',
    'sys/socket.h',
    'wchar.h',
    'inttypes.h',
    'semaphore.h',
    'sys/stat.h',
    'wctype.h',
    'iso646.h',
    'setjmp.h',
    'sys/statvfs.h',
    'wordexp.h',
    'langinfo.h',
    'signal.h',
]

HEADERS_CXX = [
    'algorithm',
    'future',
    'numeric',
    'strstream',
    'any',
    'initializer_list',
    'optional',
    'system_error',
    'array',
    'iomanip',
    'ostream',
    'thread',
    'atomic',
    'ios',
    'queue',
    'tuple',
    'bitset',
    'iosfwd',
    'random',
    'type_traits',
    'chrono',
    'iostream',
    'ratio',
    'typeindex',
    'codecvt',
    'istream',
    'regex',
    'typeinfo',
    'complex',
    'iterator',
    'scoped_allocator',
    'unordered_map',
    'condition_variable',
    'limits',
    'set',
    'unordered_set',
    'deque',
    'list',
    'shared_mutex',
    'utility',
    'exception',
    'locale',
    'sstream',
    'valarray',
    'execution',
    'map',
    'stack',
    'variant',
    'filesystem',
    'memory',
    'stdexcept',
    'vector',
    'forward_list',
    'memory_resource',
    'streambuf',
    'fstream',
    'mutex',
    'string',
    'functional',
    'new',
    'string_view',
    #
    # C compatible headers in C++
    #
    'cassert',
    'cinttypes',
    'csignal',
    'cstdio',
    'cwchar',
    'ccomplex',
    'ciso646',
    'cstdalign',
    'cstdlib',
    'cwctype',
    'cctype',
    'climits',
    'cstdarg',
    'cstring',
    'cerrno',
    'clocale',
    'cstdbool',
    'ctgmath',
    'cfenv',
    'cmath',
    'cstddef',
    'ctime',
    'cfloat',
    'csetjmp',
    'cstdint',
    'cuchar',
]


class Matcher:
    def is_match(self, path: str, orig_path: str, my_filename: str) -> bool:
        raise NotImplementedError('abstract class')


class MatcherRe(Matcher):
    def __init__(self, regex_str: str):
        self.regex = re.compile(regex_str)

    def is_match(self, path: str, orig_path: str, my_filename: str) -> bool:
        return self.regex.fullmatch(path) is not None


class MatcherHardcoded(Matcher):
    def __init__(self, headers: typing.List[str]):
        self.allowed = set(headers)

    def is_match(self, path: str, orig_path: str, my_filename: str) -> bool:
        return orig_path in self.allowed


class MatcherPairHeader(Matcher):
    def is_match(self, path: str, orig_path: str, my_filename: str) -> bool:
        return False


DEFAULT_RULES = {
    'rules': [
        {'matchers': [{'virtual': '@pair'}]},
        {'matchers': [{'virtual': '@std-c'}]},
        {'matchers': [{'virtual': '@std-cpp'}]},
        {'matchers': [{'regex': '/usr/include/.*'}]},
    ],
}


def extract_fname(path: str) -> str:
    return path.rsplit('/', 1)[-1]


def is_pair_header(cpp_filename: str, filename: str) -> bool:
    if not cpp_filename.endswith('.cpp'):
        return False
    if not filename.endswith('.hpp'):
        return False

    return extract_fname(cpp_filename[:-3]) == extract_fname(filename[:-3])


def remove_extention(filename: str) -> str:
    return filename.rsplit('.', 1)[0]


def select_pair_header(
        includes: typing.List[Include], my_filepath: str,
) -> Include:
    # Trying to find the best match at the end of the path
    my_filepath_parts = my_filepath.split('/')
    my_filename_wo_extention = remove_extention(my_filepath_parts[-1])

    max_score = 0
    scored_include = None

    for inc in includes:
        inc_parts = inc.real_path.split('/')

        min_len = min(len(inc_parts), len(my_filepath_parts))
        score = 0

        if remove_extention(inc_parts[-1]) != my_filename_wo_extention:
            continue

        for i in range(2, min_len):
            if my_filepath_parts[-i] == inc_parts[-i]:
                score += 1
            else:
                break

        if score > max_score:
            max_score = score
            scored_include = inc

    return scored_include


def sort_includes(
        includes: typing.List[Include], my_filename: str, config: 'Config',
) -> typing.List[typing.List[str]]:
    res: typing.List[typing.List[str]] = [[] for _ in config.rules]

    if config.has_pair_header:
        pair_header = select_pair_header(includes, my_filename)

    for inc in includes:
        line = inc.include_line

        match = None
        for i, matchers in enumerate(config.rules):
            match = None
            for matcher in matchers:
                if isinstance(matcher, MatcherPairHeader) and pair_header:
                    if inc.orig_path == pair_header.orig_path:
                        match = True
                        break
                match = matcher.is_match(
                    inc.real_path, inc.orig_path, my_filename,
                )
                # The first match wins
                if match:
                    break
            if match:
                res[i].append(line)
                break

        if not match:
            raise Exception(f'Include "{line}" doesn\'t match any pattern')

    for group in res:
        group.sort(key=lambda x: (not x.endswith('.h>'), x))
    return res


def write_includes(
        res: typing.List[typing.List[str]], ofile: typing.TextIO,
) -> None:
    for includes in res:
        need_newline = False

        for inc in includes:
            ofile.write(inc)
            ofile.write('\n')
            need_newline = True

        if need_newline:
            # separate include sections
            ofile.write('\n')


# The cache of a long 'cc ...' command output
# dictionary: cmdline_string -> file path
class RealpathCache:
    def __init__(self):
        self.cache: dict = {}

    def find(self, key: typing.Any) -> typing.Optional[str]:
        return self.cache.get(key)

    def set(self, key: typing.Any, value: str) -> None:
        self.cache[key] = value


# Returns the absolute path of a header from 'include_line'
def include_realpath_cached(
        source_filepath: str,
        include_line: str,
        compile_commands: typing.Dict[str, CCEntry],
        realpath_cache: RealpathCache,
) -> str:
    directory = os.path.dirname(source_filepath)

    key = (include_line, ' '.join(compile_commands), directory)
    entry = realpath_cache.find(key)
    if entry:
        return entry

    result = include_realpath(source_filepath, include_line, compile_commands)
    if result:
        realpath_cache.set(key, result)
    return result


def include_realpath(
        source_filepath: str,
        include_line: str,
        compile_commands: typing.Dict[str, CCEntry],
) -> str:
    filepath = os.path.abspath(source_filepath)

    directory = os.path.dirname(source_filepath)
    tmp = tempfile.NamedTemporaryFile(suffix='.cpp', dir=directory)
    tmp_name = tmp.name
    tmp.write(include_line.encode())
    tmp.write('\n'.encode())
    tmp.flush()

    command = compile_commands.get(filepath)
    if not command:
        raise Exception(
            f'Failed to find "{filepath}" in compile_commands.json',
        )
    command_items = adjust_cc_command(command) + [tmp_name]

    tmp2 = open(tmp_name)
    with subprocess.Popen(
            command_items,
            stdin=tmp2,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
    ) as proc:
        out, err = proc.communicate(timeout=10)
        return_code = proc.returncode
        if return_code != 0:
            sys.stderr.write(err.decode('utf-8'))
            raise Exception('Compilation attempt failed, see stderr')

        result = None
        for line in out.decode('utf-8').split('\n'):
            if not line.startswith('#'):
                continue

            if '/' not in line or tmp_name in line:
                continue

            # The first line with '/' is our file's full path.
            # Example:
            # 1 "/home/segoon/projects/taxi/userver/submodules/googletest/googletest/include/gtest/gtest.h" 1 3
            line = line.split('"', 2)[1]
            line = os.path.realpath(line)
            if result is None:
                result = line
                proc.kill()
                return result

    raise Exception(
        f'Header not found ({include_line}), '
        f'broken compile_commands.json?',
    )


class Config:
    def __init__(self, contents: dict):
        rules_matrix = contents['rules']
        result = []
        has_pair_header = False
        for rules in rules_matrix:
            out: typing.List[Matcher] = []
            for rule in rules['matchers']:
                if 'regex' in rule:
                    out.append(MatcherRe(rule['regex']))
                elif 'virtual' in rule:
                    vname = rule['virtual']
                    if vname == '@std-c':
                        out.append(MatcherHardcoded(HEADERS_C))
                    elif vname == '@pair':
                        has_pair_header = True
                        out.append(MatcherPairHeader())
                    elif vname == '@std-cpp':
                        out.append(MatcherHardcoded(HEADERS_CXX))
                    else:
                        raise Exception(f'Unknown "virtual: {vname}')
                else:
                    raise Exception(f'Unknown matcher type: {rule}')
            result.append(out)

        self.rules = result
        self._has_pair_header = has_pair_header

    def has_pair_header(self) -> bool:
        return self._has_pair_header


def is_pragma_once(line: str) -> bool:
    return line.strip() == '#pragma once'


@dataclasses.dataclass
class IncludeMap:
    # .hpp -> .cpp
    data: typing.Dict[str, str]


def handle_single_file(
        filepath: str,
        filepath_for_cc: str,
        compile_commands: dict,
        args: int,
        realpath_cache: RealpathCache,
        config: Config,
        include_map: IncludeMap,
) -> None:
    try:
        print(f'handling file {filepath}...')
        do_handle_single_file(
            filepath,
            filepath_for_cc,
            compile_commands,
            args,
            realpath_cache,
            config,
            include_map,
        )
    except Exception as exc:
        print(f'Failed to process "{filepath}", skipping (the error: {exc})')


def do_handle_single_file(
        filename: str,
        filename_for_cc: str,
        compile_commands: dict,
        args: int,
        realpath_cache: RealpathCache,
        config: Config,
        include_map: IncludeMap,
) -> None:
    orig_file_contents = read_file_contents(filename).split('\n')
    if not orig_file_contents[-1]:
        orig_file_contents = orig_file_contents[:-1]

    assert orig_file_contents

    i = -1  # for pylint
    has_pragma_once = False
    includes = []
    for i, line in enumerate(orig_file_contents):
        line = line.strip()

        if is_pragma_once(line):
            has_pragma_once = True
            continue

        if not is_include_or_empty(line):
            break

        if not line.strip():
            continue
        abs_include = include_realpath_cached(
            filename_for_cc, line, compile_commands, realpath_cache,
        )

        orig_path = extract_file_relpath(line)
        includes.append(
            Include(
                include_line=line, orig_path=orig_path, real_path=abs_include,
            ),
        )
        if abs_include not in include_map.data:
            include_map.data[abs_include] = filename

    assert i != -1

    sorted_includes = sort_includes(includes, filename, config)

    tmp_filename = filename + '.tmp'
    with open(tmp_filename, 'w') as ofile:
        if has_pragma_once:
            ofile.write('#pragma once\n\n')
        write_includes(sorted_includes, ofile)

        for line in orig_file_contents[i:]:
            ofile.write(line)
            ofile.write('\n')
    os.rename(src=tmp_filename, dst=filename)


def read_config(filepath: typing.Optional[str]) -> Config:
    if not filepath:
        print('loaded default rule set')
        return Config(DEFAULT_RULES)

    with open(filepath, 'r') as ifile:
        contents = json.load(ifile)
        print(f'loaded {filepath} rule set')
        return Config(contents)


def collect_files(
        root: str, suffixes: typing.List[str],
) -> typing.Iterable[str]:
    for dirpath, _, files in os.walk(root):
        for file in files:
            for suffix in suffixes:
                if file.endswith(suffix):
                    yield os.path.join(dirpath, file)
                    break


def collect_all_files(
        paths: typing.List[str], suffixes: typing.List[str],
) -> typing.List[str]:
    headers = []
    for filepath in paths:
        if os.path.isfile(filepath):
            headers.append(filepath)
        elif os.path.isdir(filepath):
            for header in collect_files(filepath, suffixes):
                headers.append(header)
    return headers


def has_suffix(filepath: str, suffixes) -> bool:
    for suffix in suffixes:
        if filepath.endswith(suffix):
            return True
    return False


def main():
    parser = argparse.ArgumentParser(
        description=(
            'Sorts C/C++ "#include" directives based on user rules. '
            'The tool asks C/C++ compiler for header file path resolution. '
            'Compilation cmdlines are extracted from "compile_commands.json".'
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        'paths',
        nargs='*',
        help=(
            'Path to sort. Can be a file or a directory. If it is '
            'a directory, recursively traverse it. Can be used multiple times.'
        ),
    )
    parser.add_argument(
        '--compile-commands',
        '-c',
        type=str,
        default='compile_commands.json',
        help='Path to "compile_commands.json" file.',
    )
    parser.add_argument(
        '--config', '-d', type=str, help='Path to config file.',
    )
    parser.add_argument(
        '--hpp-suffixes', '-p', type=str, default='.hpp,.h', help='TODO',
    )
    parser.add_argument(
        '--cpp-suffixes',
        '-s',
        type=str,
        default='.cpp,.cc',
        help=(
            'Source code file suffixes to use while traversing the directory '
            'separated with comma.'
        ),
    )
    args = parser.parse_args()
    process(args)


def process(args):
    suffixes = args.cpp_suffixes.split(',')
    hpp_suffixes = args.hpp_suffixes.split(',')
    realpath_cache = RealpathCache()
    compile_commands = read_compile_commands(args.compile_commands)
    config = read_config(args.config)
    include_map = IncludeMap(data={})

    headers = collect_all_files(args.paths, suffixes + hpp_suffixes)

    # process .cpp
    for hdr in headers:
        if has_suffix(hdr, suffixes):
            handle_single_file(
                hdr,
                hdr,
                compile_commands,
                args,
                realpath_cache,
                config,
                include_map,
            )

    # process .hpp
    for hdr in headers:
        if has_suffix(hdr, hpp_suffixes):
            abs_path = os.path.abspath(hdr)
            init_cpp = include_map.data.get(abs_path)
            if not init_cpp:
                print(f'Error: no .cpp file includes "{hdr}"')
                continue

            handle_single_file(
                hdr,
                init_cpp,
                compile_commands,
                args,
                realpath_cache,
                config,
                IncludeMap({}),
            )


if __name__ == '__main__':
    main()
