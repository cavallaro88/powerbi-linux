# Optional resource settings

Starting with RPM **0.1.0-2**, the default is `unlimited`: no project RAM/swap
ceiling or CPU quota. WebView2/V8 chooses its heap policy. The project supplies
no old-space cap, renderer process ceiling or economy browser flags. Operating
system, browser and hardware limits still apply. ANGLE/D3D11 and composition
compatibility flags remain enabled.

```bash
# Show the effective settings without changing them:
pbi-linux profile
# Restore the default:
pbi-linux profile unlimited
# Optional limits; omitted options keep their current values:
pbi-linux profile --memory-max 8G --swap-max 2G --webview-heap 1024
pbi-linux profile --cpu-quota 200%
pbi-linux profile --renderer-process-limit 2 --browser-mode economy
# Remove selected limits:
pbi-linux profile --memory-max unlimited --swap-max unlimited --cpu-quota unlimited
pbi-linux profile --webview-heap auto --renderer-process-limit auto --browser-mode standard
```

Settings persist in XDG configuration and apply to the **next session**. Close
all Power BI windows, allow the broker to exit, then reopen. Changing settings
never terminates an active document. Additional opens in the same session keep
that session's policy. No repair, runtime rebuild or new prefix is needed.

| Option | Default | Optional values |
|---|---|---|
| `--memory-max` | `unlimited` | Positive integer with `M` or `G` suffix |
| `--swap-max` | `unlimited` | Same units; `0` disables session swap |
| `--cpu-quota` | `unlimited` | Positive percentage; `100%` equals one logical CPU, `200%` two |
| `--webview-heap` | `auto` | 128–8192 MiB; V8 old-space cap, not total browser memory |
| `--renderer-process-limit` | `auto` | 1–128; Chromium retains its own process rules |
| `--browser-mode` | `standard` | `economy` enables process-per-site, low-end mode and disables spare renderers |

RAM/swap/CPU ceilings cover the shared session and its documents. Heap settings
do not reserve RAM. `auto` removes the project's explicit heap cap; the browser
retains its internal limits. See [V8's heap policy](https://chromium.googlesource.com/v8/v8/+/73f21fd09b6b2b9930dbed725bbbde78de4e1710/src/heap/heap.cc).

`normal` and `large` remain explicit economy presets:

| Preset | RAM | Swap | V8 old-space | Renderers | Browser mode |
|---|---|---|---|---|---|
| `unlimited` (default) | Unlimited | Unlimited | Auto | Auto | Standard |
| `normal` | 6 GiB | 2 GiB | 512 MiB | 2 | Economy |
| `large` | 10 GiB | 4 GiB | 512 MiB | 2 | Economy |

Select with `pbi-linux profile normal` or `pbi-linux profile large`. A preset
replaces all resource settings; options in the same command then override that
preset. `pbi-linux profile unlimited` clears caps and economy settings together.

Release 1 wrote normal/large presets automatically. Exact legacy presets are
interpreted as unlimited after upgrading; reading does not rewrite settings.
Custom legacy values are retained. New explicit choices carry
`resource_schema: 2` and are preserved on later launches.

Earlier synthetic refresh/Save/two-hour evidence used bounded profiles. It
remains evidence for those settings. The new default needs a separate native
workload check. The user's reported improvement after removing cgroup limits
motivated this change; it does not isolate V8 garbage collection as the cause.
