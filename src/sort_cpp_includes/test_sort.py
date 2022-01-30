import typing
import pytest
import dataclasses
import json

from . import sort_cpp_includes


@dataclasses.dataclass(frozen=True)
class FakeArgs:
    paths: typing.List[str]
    compile_commands: str
    config: str
    hpp_suffixes: str
    cpp_suffixes: str


# TODO: ad-hoc
COMPILER = '/usr/bin/clang++-9'


def compose_compile_commands(args):
    result = []
    for arg in args:
        result.append({
            'command': ' '.join([f'{COMPILER}', '-c', arg, '-o', f'{arg}.o']),
            'directory': '/',
            'file': arg,
            },
        )
    return result


@pytest.fixture
def check(tmp_path):
    def _check(input_cpp: str, expected_output: str, rules: dict):
        input_fname = tmp_path / 'input.cpp'
        with open(input_fname, 'w') as ifile:
            ifile.write(input_cpp)

        cc = compose_compile_commands([str(input_fname)])
        cc_fname = tmp_path / 'compile_commands.json'
        with open(cc_fname, 'w') as cc_file:
            cc_file.write(json.dumps(cc))

        config_fname = tmp_path / 'sorting-rules.json'
        with open(config_fname, 'w') as config_file:
            config_file.write(json.dumps(rules))

        args = FakeArgs(
                paths=[str(input_fname)],
                compile_commands=str(cc_fname),
                config=config_fname,
                hpp_suffixes='.hpp,.h',
                cpp_suffixes='.cpp,.cc',
                )
        sort_cpp_includes.process(args)

        with open(input_fname, 'r') as ifile:
            contents = ifile.read()

        print(contents)
        print(expected_output)
        assert contents == expected_output

    return _check


def test_empty(tmp_path, check):
    input_cpp="""#include <iostream>
#include <atomic>
#include <cstdio>
"""

    expected_output="""#include <atomic>
#include <cstdio>
#include <iostream>
"""

    rules = {
            'rules': [
                {'matchers': [
                    {'regex': '.*'},
                    ],
                    },
                ],
            }
    check(input_cpp, expected_output, rules)
