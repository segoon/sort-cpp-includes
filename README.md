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
sort-cpp-includes --compile-commands compile_commands.json src/ include/
sort-cpp-includes --compile-commands compile_commands.json src/ include/
```

`compile_commands.json` can be generated via `cmake` or vscode.
After the successful run you might notice changes in your source files.


## Implementation

To properly split includes into groups separated by newlines, we have to know
the full paths of the included header files. The full path is used to identify
an include group according to the user policy. E.g. '#include <os.hpp>` may include
`$PWD/os.hpp`, `/usr/include/os.hpp`, and so on. sort-cpp-includes doesn't
resolve includes by itself, it uses a C++ compiler's ability to preprocess
your source files.


## Errata

* Sourceless header files: you have to include each header into matched .cpp files
  at least once.
* sort-cpp-includes was tested on clang only, so sorting with alternative compilers
  might not work as expected.
