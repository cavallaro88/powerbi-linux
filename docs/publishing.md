# Publishing and the Windows Store rating prompt

On October 18, 2026, the user published a real report to a homologation workspace,
saw the success confirmation, then encountered `System.Runtime.WindowsRuntime,
Version=4.0.0.0` missing. The user subsequently confirmed that the report appears
and opens in Power BI Service. This is user-confirmed publication evidence;
cloud publication was not repeated or independently queried by the agent.

Inspection of the pinned Desktop assembly identified the success-only
`RunPostPublishTasks` call to `StoreRating.PromptForRatingAsync`. Its async state
machine contains `Windows.System.Launcher.LaunchUriAsync` and a WinRT awaiter for
`ms-windows-store://review/`. JIT compilation requires the missing assembly even
when the UWP gate would skip the prompt. An offline invocation with **all service
fields null**, no window and no report reproduced the same missing-assembly
exception in that state machine, before any service access.

RPM 10 compiles the project's guarded `PatchStoreRating.cs` during setup/repair.
It replaces only this rating entrypoint with a completed .NET Task. Fedora has no
Windows Store integration; the publication request, result handling, labels,
authentication, post-publish save logic and other error handling are preserved.
The correction does not install a replacement Microsoft DLL or implement WinRT.

The private candidate changed one method among **29,697** inspected methods;
all embedded resources were unchanged. Its offline entrypoint completed with
all dependencies null. The public regression wrapper also passed. This is
separate from performing another cloud publication with the corrected assembly.

## Existing installations

Close Desktop before maintenance. Upgrade the CLI RPM, then run `pbi-linux repair`
to apply the recipe to a new managed profile, following its normal disk-space
requirements. Runtime 0.1.3 remains compatible and does not need rebuilding.
The notebook validation used bounded local maintenance with an assembly/metadata
backup and no full prefix copy. An RPM upgrade alone does not rewrite an already
provisioned per-user Desktop assembly. Repair using an older RPM recipe removes
this new correction.

Offline regression, from the source tree:

```bash
python3 tools/test-store-rating.py
# Or test an unactivated private candidate:
python3 tools/test-store-rating.py --assembly-dir /path/to/candidate
```

The test compiles an own console helper and loads the installed/candidate assembly
in its own process. It constructs no services, accesses no real report, supplies
no account and makes no publishing request. It uses the managed .NET environment;
logs/results stay private under `.local/store-rating/`. The components QA suite
runs it only with its dedicated QA installation.

Confirm a publication in the intended Service workspace before treating it as
successful. This correction addresses a local follow-up prompt and does not turn
an unsuccessful upload into a success. Broader cloud, sensitivity-label and
workspace scenarios remain unvalidated.
