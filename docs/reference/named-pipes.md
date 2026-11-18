# Named pipe listing

## Tools found no running Desktop (2026-11-18)

With a report open in Desktop, the Windows build of the pbir CLI, run with the
runtime's Wine in Desktop's prefix, reported that no Desktop was running.
`pbir desktop list`, `pbir desktop refresh`, `pbir desktop screenshot` and
`pbir model -q` against the open report all failed that way.

Desktop's local API listens on a named pipe,
`\\.\pipe\pbi-desktop-bridge-<PID>`, and pbir finds it by listing `\\.\pipe\`.
Wine 11.18 failed every listing of that directory with
`STATUS_BAD_DEVICE_TYPE`: the directory is a server object with no Unix
directory behind it, and `NtQueryDirectoryFile` reads only Unix directories.
`FindFirstFile` on `\\.\pipe\*`, Python's `os.listdir` and .NET's
`Directory.GetFiles` failed alike. Opening a pipe by its full name always
worked, so a client that already knows the name was never affected.

`wine-11.18-named-pipe-directory.patch` lets the server list the pipes and
ntdll format them for every directory information class. As on Windows:

- an entry's size is the pipe's current instance count, its allocation size
  the maximum instance count, and its attributes `FILE_ATTRIBUTE_NORMAL`;
- the search mask of the first query is kept for the handle, so a later query
  without a mask goes on with it; a restart with a new mask replaces it;
- a first query that matches nothing returns `STATUS_NO_SUCH_FILE`, a later
  one `STATUS_NO_MORE_FILES`;
- listing needs `FILE_LIST_DIRECTORY` access.

### Evidence

`python3 tools/test-pipe-directory.py --runtime /path/to/runtime` compiles
`tests/e2e/pipe-directory-probe.c` and runs it in a new prefix, which it
removes afterwards. The probe creates its own pipes and lists them through
`FindFirstFile` and `NtQueryDirectoryFile`: every directory information class,
the kept mask, a restart, an entry truncated by a small buffer, no match, no
access, a closed pipe and 1,100 pipes read through `FindNextFile`.

| Runtime | Checks passed | Checks failed |
|---|---|---|
| 0.1.6-beta.1, published | 14 | 27 |
| Built from this change with `runtime/build.py` | 75 | 0 |

With a runtime carrying the patch (built from a tree that also carries the
Arch and Hyprland changes) and a test report open in Desktop 2.159.1231.0,
`pbir desktop list` named the report and its pages, `pbir desktop refresh`
reloaded a visual title changed on disk and `pbir desktop screenshot` saved
the page. `pbir model -q` loads an ADOMD.NET client, as it does on Windows;
given one, it returned the query result from the open model.

Limits:

- One host and one Desktop build.
- The position of a listing is an index into the server's pipe table, so a
  pipe created or closed while a listing is under way can be skipped or listed
  twice.
- A query with an event or APC is refused, as for every directory in Wine.
