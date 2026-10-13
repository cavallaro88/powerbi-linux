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

An interactive account test is still required to validate Microsoft
authentication, MFA, token persistence, restart and service access. Credentials
belong in the Microsoft authentication interface. Reports and account/token
caches must not be included in bug reports or public evidence.

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
