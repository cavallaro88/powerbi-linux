# Contributing

Start with the README and build guide. Changes should include a concise explanation of the behavior, a synthetic reproducer and relevant validation. Run `python3 -m unittest discover -s tests/unit -v` and validate desktop entries with `desktop-file-validate`.

Keep production features separate from diagnostic instrumentation. Add a version/expected-input check before introducing any proprietary binary workaround. Record patch origin, license, target version and observed effect. No fabricated success, credential bypass or silent TLS downgrade is acceptable.

A new runtime release must pass the compatibility matrix on Fedora 44. Backend refresh success alone is not UI certification. Existing investigation evidence cannot substitute for testing the new build.

Contributions are licensed under the applicable file/component license. Preserve upstream notices. Do not submit Microsoft binaries, customer data, secrets, populated prefixes or evidence containing private information. Public issue templates request doctor output and synthetic reproduction steps.
