# Native installed RPM — 2026-10-13 follow-up

The exact `powerbi-linux-0.1.0-1.noarch.rpm` was installed by the user with DNF
on Fedora 44 x86_64, GNOME native Wayland. Its SHA-256 remains:

```text
799d2d2f3014475c784ee1041de8f251ba098c070a28e5886fca9817fed06379
```

Setup completed through `/usr/bin/pbi-linux` from official installers with the
same verified source-built runtime as the [initial validation](validation.md).
It used normal user XDG directories and system NTLM/ODBC. All doctor checks
passed, including installed patches and derived PE cache. `rpm -V` was clean;
42 installed code/runtime-resource files matched the checkout. Every broker
observation loaded `/usr/share/powerbi-linux/src`.

| Check | Result |
|---|---|
| Synthetic PBIX native frame | Cafe 120, Suco 100, Cha 80, Total 300 reviewed in a submitted native frame; independent DAX confirmed 300. Frame age 0.082 seconds. |
| Production GIO PBIX | Two simultaneous documents, Unicode/spaces, both native windows responsive and both totals 300. |
| Production GIO PBIP / PBIR | Project/model/report relative paths passed; totals 300 and native windows responsive. |
| Production session resources | Normal 6 GiB RAM / 2 GiB swap limits, diagnostics disabled, no OOM. Dual-document peak RAM 6.00 GiB; ending swap 1.18 GiB. |

The first dual-document test used an incorrect table name for the CSV-derived
model. Its failed query is retained in `host-rpm/test-recipe-error`; correcting
the test recipe required no product code changes.

Selected sanitized evidence is in `host-rpm/` inside the companion QA archive.
This follow-up opens existing saved synthetic reports; it does not repeat Save,
UI refresh or the two-hour soak. Those remain the earlier runtime checks.
Microsoft sign-in/cloud publishing, arbitrary enterprise models/connectors
and the earlier discrepant idle native sample retain their documented limits.
The RPM/SRPM binaries remain unchanged; source/QA archive updates add this
follow-up documentation and evidence.
