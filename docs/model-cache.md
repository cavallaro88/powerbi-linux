# Saving and restoring cached PBIP models

`cache.abf` holds the local semantic model and imported data. When it exists,
Desktop loads that image and then applies the project's semantic model
metadata. Definitions alone do not contain the imported rows. This behavior is
documented by [Microsoft](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset).
This cache is independent of this project's derived PE loader cache.

## Isolated failure and correction

The October 18 failure occurred **after** image loading, during model metadata
synchronization in `TmslApplier`. The restored model contained 158 tables and
answered local data queries. Of 169 compared TMDL files, 167 were identical; the
remaining differences were database runtime properties and formatting of the same
linguistic JSON. That JSON describes natural-language metadata; see
[Microsoft's object contract](https://learn.microsoft.com/en-us/dotnet/api/microsoft.analysisservices.tabular.linguisticmetadata).

The original multiline content had 4,211,895 characters; the compact equivalent
had 2,452,777. Changing only that formatting in a private project copy allowed
opening with the same ABF. Direct metadata-only engine tests reproduced the
failure without Desktop's loader: original multiline JSON failed, compact JSON
passed, and a larger 4,300,000-character space-padded equivalent passed. Adding
many line breaks reproduced the error. This rules out a general 4 MB size limit
and isolates a multiline-content failure on the tested local stack; the exact
closed-source engine/internal Wine boundary is not established.

RPM 11's helper removes JSON whitespace outside strings **in memory**, then
checks parsed equivalence. String contents, escape sequences, numeric tokens and
property order remain intact. Invalid/unsupported input is left for the original
model API to handle. Only two instructions are inserted before the original
`CopyModelPreservingHigherCompatibilityLevel` body. Compatibility-level handling,
model copy, metadata update, query changes and save behavior remain in control of
Desktop. No synchronization step is bypassed, and no source file or original
cache is removed by the patch.

## Evidence and limits

- Ten offline helper checks passed, covering quoted whitespace/escapes, large
  integers, decimal precision, idempotence, malformed input and in-memory objects.
- One method among 29,697 compared methods changed; embedded resources matched.
  The helper's strong-name signature was independently verified.
- A genuine new measure was added only to a private TMDL copy. It evaluated to
  73 after loading with the unchanged original cache, proving source metadata
  changes were applied.
- Desktop's own Save callback wrote a new ABF in that private copy. A graceful
  close and a fresh **normal launcher** session restored it without refresh.
  Independent local queries found the same row counts/states for all 158 tables
  and the new measure still returned 73. One table already returned a query
  error before Save; the same state after reopen is not reported as recovered
  data. The tests did not compare every cell or revalidate source-server refresh.
- The original report definitions and cache were preserved. Customer models,
  ABF files, screenshots and detailed model logs are excluded from public QA.

The result does not imply that every unreadable ABF is intact. Preserve an
original file while diagnosing it; do not automatically delete caches to make
an empty model open.

## Backup and recovery procedure

1. Save through Desktop and wait for completion; close Desktop before copying
   project files. Keep a versioned backup of the **whole project**, including
   report files, semantic definitions and the hidden `.pbi/cache.abf`. Ordinary
   Git excludes ABF, so a Git checkout alone is not a populated-model backup.
2. Restore that matching set to a separate directory first, retaining the
   original backup. Keep the report-to-model relative paths intact. Replacing
   just ABF while using unrelated definitions can lead Desktop to apply those
   definitions to the cached model and invalidate data for changed partitions.
3. Open the restored PBIP with the compatible installation. Verify known totals
   or table counts **before refresh**, then save, close and reopen that copy.
   Reopening without source refresh is the check that cached data persisted.
4. A missing ABF requires source refresh to recover imported rows. An ABF alone
   is not a complete report backup and does not replace report layout, the PBIP
   entry point or the project's authoritative definitions. It is not a portable
   backup of sign-in or source credentials either.

ABF contains business data even when the project definitions are safe to share.
Keep populated backups private; bug reports should use a synthetic reproducer.
This release does not implement an automatic backup/rotation service or promise
recovery of arbitrary damaged ABF files. The validated path uses Desktop's own
save and load implementation.

## Installation and regression

Existing profiles need the RPM 11 recipe applied with Desktop closed; the usual
`pbi-linux repair` creates a new managed profile and needs its documented free
space. Runtime 0.1.3 does not need rebuilding. This notebook used bounded local
maintenance with assembly/metadata backups and an idle Wine session, then tested
the installed files. An RPM upgrade alone does not re-patch an existing profile.

The helper is built from project sources with the installed .NET compiler and
Desktop's existing Newtonsoft.Json dependency, then signed with a locally
generated key. Microsoft binaries remain local. Diagnostic normalization does
not upload reports, refresh data sources or choose credentials.

```bash
python3 tools/test-cache-compatibility.py
```

This public component test uses own objects and strings and touches no report or
engine. The components QA suite runs it in its dedicated installation. Full
Save/reopen coverage additionally requires a disposable populated model, a real
Desktop Save, a fresh engine session and independent data checks. Missing ABF or
unchanged file timestamps do not count as successful cache persistence.
