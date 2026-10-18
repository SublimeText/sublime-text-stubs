The `python314/` folder was extracted from ST build 4213
(https://download.sublimetext.com/sublime_text_build_4213_x64.tar.xz).
It is distributed with permission of Sublime HQ Pty Ltd
under the terms in [LICENSE](LICENSE).

To extract the sources of the latest build,
or of a specific one, run from the repository root:

```sh
uv run --directory tools python update_reference.py              # the latest build, if newer
uv run --directory tools python update_reference.py --build <N>  # build <N>
```

Besides the sources,
the script also bumps `ST_BUILD` in `tools/generate_stubs.py`
and the build number at the top of this file,
and it refuses a build whose plugin host is not `python314`.

`python314` names the Python version of the plugin host,
so it only changes when a build ships a new one.

`Lib/python314/imp.py` is deliberately not taken:
it is a compatibility shim, not part of the plugin API.
Neither is the `Lib/python33/` directory,
which belongs to the deprecated Python 3.3 plugin host that these stubs do not target.
