# Edit Permissions — runtime 0.1.1 / RPM 8 candidate

On Fedora 44 GNOME Wayland, Privacy Level and OK could fail independently in
Edit Permissions. Explicit Win32 activation alone did not fix the pointer issue.
The source-list resize addresses a separate blank-list problem.

## Corrections and evidence

The old Wine parent patch passed a transient owner into surface-role selection,
so an owned modal could become a subsurface of its disabled main window. The
new driver separates child parenting from transient ownership, keeps borderless
modals managed while a dropdown has focus, and attaches borderless owned tool
popups to their anchor. An invisible WinForms parking owner falls back to the
visible window beneath the popup. Client surfaces track their actual parent;
subsurface stacking is restricted to valid siblings.

The first candidate failed full Desktop testing with an invalid parent/sibling
Wayland request; the next still misplaced the popup. Neither was activated.
The final driver passed the complete synthetic flow and its patch, prepared
sources and manifest are synchronized. No rejected experiment remains in the
build recipe.

OK also failed after receiving a click: Knockout traversed native host/button
objects and raised TargetParameterCountException while pulling the view model
before closing. The permission backend can save the choice before this exception;
a retained value alone does not prove OK works. RPM 8 serializes only the 13
original permission view-model fields. Original privacy/encryption handlers and
values remain in control; the patch supplies no passwords or credential modes.
Exact original/output hashes and unchanged PE/resource sizes guard the change.

A disposable two-table PBIP and its own CSV passed pointer input through the
GNOME compositor: selection, modal disappearance after OK, reopen with the saved
choice, another selection followed by Cancel, and reopen with the previous
choice. Repeated modals passed. A separate serializer check preserved Database
and encryption=true while native host/button getters deliberately threw if read;
neither getter was touched. The isolated WinForms/HTML fixture received all three
expected callbacks with the final driver; the earlier baseline received none.

The complete recipe produces this tested Microsoft.Mashup.Client.UI.dll hash:

```text
8aee5abdd62ef384f49e08cb9931093dab7a1b8df1ddb885af9d0b1ea4358c62
```

The powerbi-linux-runtime-0.1.1-x86_64.tar.xz archive has SHA-256:

```text
d6cfeccb3c9e11167815794cac2dbf4d09f665f2034e6db93b8462ea36034d50
```

It incrementally rebuilds only lib/wine/x86_64-unix/winewayland.so in the original
pinned builder. All other payload files, their file set and source locks match
the verified 0.1.0 baseline. The final patch applies without fuzz to three upstream
driver files. This evidence does not transfer the old 158-table/two-hour
certification to the new checksum. Full release gates and arbitrary enterprise
reports remain outside this check. Real MySQL refresh/authentication/TLS remain
separate. The real report's 452 baseline files were unchanged by the investigation.

**Nested-dialog limitation:** None on a source without credentials or native
query approvals opens Delete Permissions. That separate confirmation stayed at
2×2 with HTML still loading during synthetic cleanup. It was cancelled on the
exact test window. Do not describe that path as fixed, clear unrelated
permissions or remove project caches.

## Installation and reproduction

The RPM carries the HTML recipe and doctor checks; the runtime archive carries
the driver. Upgrading only the RPM does not activate these changes in an existing
profile. With Desktop closed and the new recipe available, verify checksums and
use `pbi-linux update --runtime ARCHIVE --runtime-sha256 SHA256`. It snapshots the
prefix and applies the HTML recipe as well as selecting the runtime. Check disk
space first: this host's prefix was about 9.1 GiB and reflink was unavailable.
Keep the previous profile for rollback. No Microsoft installer update is involved;
resource defaults remain unlimited.

A full source build uses `python3 runtime/build.py --runtime-version 0.1.1` and
is not claimed to produce a byte-identical incremental archive. For the incremental
build, start from a verified 0.1.0 runtime and the final Wine source. Configure in
the pinned builder with `--prefix=/opt/powerbi-linux --enable-archs=i386,x86_64
--disable-win16 --disable-tests --without-x --with-wayland`, make
`dlls/winewayland.drv/winewayland.so`, strip debug information and replace only
that file in a private copy. Update driver/patch hashes and incremental provenance
in runtime.json, verify every payload file and package without hardlink entries.
Do not overwrite the original archive. See [build](../development/build.md),
[legacy HTML](legacy-html.md) and [connectors](../user/connectors.md).
