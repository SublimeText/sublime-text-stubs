The `python314/` folder was extracted from ST build 4213
(https://download.sublimetext.com/sublime_text_build_4213_x64.tar.xz).
It is distributed with permission of Sublime HQ Pty Ltd
under the terms in [LICENSE](LICENSE).

To extract the sources of another build,
set `BUILD` to its number and run, from the repository root:

```sh
BUILD=4213
TARBALL="${TMPDIR:-/tmp}/sublime_text_build_${BUILD}_x64.tar.xz"
curl -fL -o "$TARBALL" "https://download.sublimetext.com/sublime_text_build_${BUILD}_x64.tar.xz"
tar -xJf "$TARBALL" --strip-components=3 -C references/python314 \
    sublime_text/Lib/python314/sublime.py \
    sublime_text/Lib/python314/sublime_plugin.py \
    sublime_text/Lib/python314/sublime_types.py
```

`python314` names the Python version of the plugin host,
so it only changes when a build ships a new one.

`Lib/python314/imp.py` is deliberately not taken:
it is a compatibility shim, not part of the plugin API.
Neither is the `Lib/python33/` directory,
which belongs to the deprecated Python 3.3 plugin host that these stubs do not target.
