# Security rules

Rules every change to powerbi-linux must keep. The security gate's review blocks a change that
breaks one, and the tests named under each rule check it on every build. A rule changes only with
the maintainer's OK.

## 1. Only your own account can reach a running Power BI session

Why: the session starts Desktop and opens files on request; another user or account on the
computer must not be able to send it requests.
Enforced by: `tests/unit/test_broker.py`, "test_only_this_user_can_reach_the_session"

## 2. Nothing downloaded is used before its checksum matches the pinned one

Why: a tampered download (a hijacked network or mirror) would otherwise run inside your Power BI.
Enforced by: `tests/unit/test_downloads.py`, "test_wrong_payload_removes_partial_file",
"test_corrupted_cached_content_is_not_trusted" and "test_insecure_download_and_redirect_are_rejected"

## 3. A normal launch never opens a remote-control (DevTools) port

Why: that port lets any program on the computer control Desktop and read your reports. Only
`pbi-linux open --diagnostics` opens it, and it warns when it does.
Enforced by: `tests/unit/test_broker.py`, "test_a_normal_session_opens_no_devtools_port" and
"test_only_diagnostics_open_a_devtools_port"; `tests/unit/test_product.py`,
"test_release_env_disables_diagnostic_inheritance"

## 4. Archives are never unpacked outside their own folder

Why: a crafted archive could otherwise overwrite your files.
Enforced by: `tests/unit/test_product.py`, "test_archive_rejects_traversal" and
"test_archive_rejects_symlink_escape"; `tests/unit/test_connectors.py`,
"test_traversal_member_cannot_escape_staging"

## 5. Microsoft files are changed only when their exact checksum is known

Why: patching an unknown build could break Desktop or hide a tampered file.
Enforced by: `tests/unit/test_recipes.py`, "test_supported_builds_reject_each_others_files";
`tests/unit/test_dialog_serializers.py`, "test_unknown_contents_are_refused";
`tests/unit/test_autorecovery.py`, "test_unknown_script_contents_are_rejected";
`tests/unit/test_desktop_config.py`, "test_verified_builds_refuse_an_unknown_configuration"

## 6. Packages are built only from main, after its checks pass, never from a pull request

Why: a pull request from anyone could otherwise publish a package that users install.
Enforced by: `tests/unit/test_ci_policy.py`, "test_package_workflow_requires_successful_main_push_checks"
