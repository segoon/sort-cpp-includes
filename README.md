## sort cpp includes

Got tired from holywars on includes order in a C++ project?
With sort-cpp-includes you can end the war!
sort-cpp-includes is able to sort include directories
according to simple grouping rules provided by the user.
You can create different rulesets for multiple projects
according to the local policy.

## Installation

Install for all users:
```(python)
pip install sort-cpp-headers
```

Or install for a single user:
```(python)
pip install --user sort-cpp-headers
```


## Gettings started

The tool is simple to use. To sort your #include's just pass it your
`compile_commands.json` and paths to header files and source files:

```bash
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ...
sort-cpp-includes --compile-commands compile_commands.json src/ include/ main.cpp
```

`compile_commands.json` can be generated via `cmake` or `vscode`.
After the successful run you might notice changes in your source files,
if the sorting order was not met before.

The tool comes with a simple sorting policy: pair header, C headers, C++ headers,
headers from /usr/include, the rest files. If it doesn't fit you, you may
define your own policy and pass it to `sort-cpp-includes` using '-d' option.
An example from Yandex.TPlatform config:

```yaml
rules:
  - matchers:
      - virtual: "@pair"

  - matchers:
      - virtual: "@std-c"

  - matchers:
      - virtual: "@std-cpp"

  - matchers:
      - regex: "/usr/include/.*"

  - matchers:
      - regex: ".*/third_party/.*"
      - regex: ".*/google-benchmark/.*"

  - matchers:
      - regex: ".*/userver/.*"
  - matchers:
      - regex: ".*/build/.*"
  - matchers:
      - regex: ".*/libraries/.*"
  - matchers:
      - regex: ".*/services/.*"
```

The sorting and grouping runs in 2 steps. First, the include group is calculated.
Adjacent include groups will be separated with a single empty line.
Second, the sorting takes place for each group, independently. Each matcher
define a sort group. It may consist of one or more matchers.
For now the following matchers are implemented:

* regex - a simple Python's `re` matcher
* virtual: @pair - the pair header (`server.hpp` for `server.cpp`)
* virtual: @std-c - standard C language headers
* virtual: @std-cpp - standard C++ language headers (C++17)

You may add several matchers to the same group, it would mean "at least one matcher
from the group must match". The first match wins, IOW, if a first group matcher
matches the include, the rest groups are skipped.

## Implementation details

To properly split includes into groups separated by newlines, we have to know
the full paths of the included header files. The full path is used to identify
an include group according to the user policy. E.g. `#include <os.hpp>` may include
`$PWD/os.hpp`, `/usr/include/os.hpp`, and so on. `sort-cpp-includes` doesn't
resolve includes by itself, it uses a C++ compiler's ability to preprocess
your source files.

## Errata

* Sourceless header files: you have to include each header into matched .cpp files
  at least once.
* `sort-cpp-includes` was tested on clang only, so sorting with alternative compilers
  might not work as expected.
* Only a single thread is used, but we could utilize more
* `sort-cpp-includes` stops searching include directives on the first non-include line
  except `#pragma once`.
