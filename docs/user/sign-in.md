# Microsoft sign-in

The email prompt uses legacy MSHTML. In Desktop 2.158.1177.0, a native Continue
click reached `EnterEmailDialog.OnDefaultButton`, then failed inside
`KoFloatingDialog.PullViewModelFromJs` with `TargetParameterCountException`.
The default Knockout serialization traversed native host/button objects in the
view model; accessing those objects during serialization invoked native methods
without their required arguments.

The compatibility recipe adds `getJSON` to this email view model. It serializes
the existing wire fields `email`, `retrySource` and `warningMessage`. Desktop's
original email validation, result handling, cancellation and authentication
remain in control. This change does not create a token or report a successful
sign-in.

The patch checks the original Desktop assembly and the exact JavaScript resource
contents, retains the original copyright notice, and preserves PE/resource sizes
and IL. Setup/repair applies it before WinRT remapping and the native save
confirmation patch. Doctor checks the resource version in the activated assembly.
Modified Microsoft binaries stay in the local installation.

## Checks completed

A fresh diagnostic Desktop copy loaded the patched resource without a runtime
assignment of the serializer. With a fictitious address, the payload contained
only the three expected fields. A native Continue click closed the email prompt
at the first observation after approximately 0.2 seconds, with no parameter-count
exception. The resource also survived the actual WinRT/save-dialog patch tools.
The Python suite passed 41 tests, including rejection of unsupported/corrupted
inputs before any application file is replaced.

On 2026-10-15, a real-account test on Fedora 44 completed Microsoft
browser authentication in Vivaldi, confirmed by the user. The diagnostic Desktop
was then closed normally and reopened through the regular production launcher;
the user confirmed that the account remained connected. No password, MFA code
or account/token cache was collected. The specific MFA challenge was not
observed or independently certified. A real homologation publication was later
confirmed by the user on October 18; its local post-success Store rating error
and scoped correction are documented in [publishing](publishing.md).
Broader cloud publishing, individual connectors,
long-term token renewal and other tenant/device policies need separate tests.

Credentials belong in the Microsoft authentication interface. Reports and
account/token caches must not be included in bug reports or public evidence.

## Browser selection

In this Desktop version, `AuthenticationManager.UseSystemBrowser` reads the
existing `UseSystemBrowserForAuthentication` preference and
`EnableMsalAuthenticationBrowserSelection`; the cloud implementation enables
the latter. The same preference therefore participates in the service sign-in
path. The local MSAL client config uses `http://localhost` for the system-browser
flow and limits broker registration to the embedded-browser path.

Microsoft documents [MSAL browser selection](https://learn.microsoft.com/en-us/entra/msal/dotnet/acquiring-tokens/using-web-browsers)
and [the Windows broker](https://learn.microsoft.com/en-us/entra/msal/dotnet/acquiring-tokens/desktop-mobile/wam).
Browser, broker availability, cloud discovery and an organization's account
policies need separate diagnosis when the email prompt completes but no
authentication page appears. No browser preference is changed by the email
serializer patch.

## Windows broker failure and working configuration

The real-account Continue click returned nonempty result data and an OK dialog
result. The following authentication step failed in the Windows native broker
with `Microsoft.Identity.Client.NativeInterop.MsalRuntimeException`,
`Status: Unexpected`, `Context: Caught exception`, tag `0x2039c1cd`.
Selecting Desktop's existing system-browser preference avoided this failure and
opened the Microsoft flow in the Fedora default browser. This is separate from
the email serialization correction.

For an existing profile, open **File → Options and settings → Options → Global →
Security → Authentication Browser**, enable **Use my default web browser**, and
restart Desktop before signing in. The tested host already has this preference
saved and does not need a package upgrade or repair to keep the working login.
The email serializer check in doctor does not certify browser selection or an
authenticated session.

Starting with the RPM 6 recipe, setup/repair compiles `ConfigureSignIn.cs` and
uses Desktop's own `LocalUISettingsStorage` and `UISettings` API to enable
`UseSystemBrowserForAuthentication`. This happens during offline provisioning,
not every launch. MSAL, Microsoft's authentication endpoints, native email
validation and account/device policies remain in control. The default browser
must be installed and usable in the graphical session.

Run `python3 tools/test-signin-settings.py` from a checkout with a prepared
installation to exercise this configuration on synthetic storage. The test
checks a disabled preference without writing, enables it, reads it in a fresh
process, repeats the change, rejects an invalid operation, and verifies that
unrelated preferences and synthetic credential/feature parts remain intact.
It never copies or modifies the real user's settings or credentials.
