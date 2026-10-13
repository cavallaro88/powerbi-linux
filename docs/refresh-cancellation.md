# Cancel during data refresh

A user reported that Cancel in the refresh progress dialog did not stop loads.
A permanent freeze was not reproduced in the following controlled Fedora 44
Wayland tests on October 14. No refresh-cancellation patch has been applied.

The test used a disposable two-table PBIP: the sales table totaled 300 and a
fact table held 200 rows. A local text file controlled an artificial delay in
Power Query. This required no external connector, credentials or customer data.

| Phase at the native Cancel click | Observed result |
|---|---|
| Evaluating a delayed query | Progress disappeared and the main window was enabled again in approximately 0.8 seconds. |
| Loading data, with a delay while evaluating each fact row | The click reached the managed host; progress changed to Cancelling. The window waited 19.879 seconds for cancellation to complete, then the main window was enabled again. |
| Data after cancellation during loading | Independent DAX still returned the previously committed total 300 and 200 fact rows. |
| Further use | A new refresh completed; Save and a fresh reopen retained the expected data and visible sales total. |

Clicks went through the Wine native input path into the actual visible Cancel
button. CDP observation recorded the button's `OnButtonClick` message. Closing
progress was checked through native window visibility and main-window enabled
state, not by assuming an old browser document had been destroyed. Desktop can
retain the hidden progress page after the native window disappears.

The inspected path is WebView2 message → UI dispatcher → overridden
`CancelAndClose` → `CancellationTokenSource.Cancel`. Loading receives that token;
`CloseDialog` awaits the load task before hiding the progress window. The observed
wait is consistent with that behavior. It does not establish why the user's
original workload appeared stuck or prove that every connector can stop promptly.

A quick click response and completed cancellation are different observations.
For a workload that remains in Cancelling, collect the phase/table, elapsed time,
progress changes, query/engine errors and connector information. Reproduce with
a disposable source where possible. Do not use forced process termination or
hiding the window as a substitute for cancellation and rollback.

For the slow-source reproducer, preserve the generator's typed columns and use
`Function.InvokeAfter` around either the complete fact-table expression or the
per-row Amount calculation. A delay of 0.2 seconds per row over 200 rows provides
time to click during loading; reset the local delay to zero for the baseline and
retry. This checks an artificial Power Query workload, not enterprise network
cancellation, server-side query termination or the original report.
