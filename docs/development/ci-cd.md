# CI/CD: checks first, packages after merge

## Policy

1. Develop and review on a feature branch. Push source, tests and documentation,
   not RPM/DEB binaries, installers, prefixes or local QA evidence.
2. **Product checks** runs on pushes, PRs, manual dispatch and schedule. Fedora
   44, Ubuntu 24.04/26.04 and Debian 13 run the repeatable quick suite. This phase
   validates source, metadata and staging but does not construct package archives
   or install the product. `PBI_PACKAGE_BUILD_TESTS=0` also disables the native
   archive-building unit test; it is opt-in, not enabled just because dpkg exists.
3. Merge the reviewed change into `main`. **Packages after merge** is triggered
   by completion of Product checks, only when that successful run was a `push`
   to `main` in this repository. It checks out the exact tested `head_sha`, not a
   moving branch tip. Feature-branch, PR, scheduled and manually dispatched checks
   cannot trigger packaging.
4. The post-merge workflow builds RPM/source RPM on Fedora 44 and experimental
   DEBs on Ubuntu 24.04/26.04 and Debian 13. It enables native archive tests,
   exercises disposable package installation/removal and the DEB lifecycle,
   and retains packages, checksums, source and check evidence as Actions artifacts
   for 14 days. A failed job may retain partial artifacts for diagnosis: these
   are not approved release downloads.
5. **Release publication remains an explicit separate operation.** No workflow
   here has `contents: write`, creates a GitHub Release, pushes tags, or updates
   the recommended release/setup download pointers. Review the exact artifacts,
   checksums, corresponding sources and applicable graphical acceptance before
   publishing. Automatic release/signing can be designed separately.

The intended path is **branch → PR/review → checks → merge → package build/test
→ explicit release approval**. Repository branch protection must require the
checks and restrict direct pushes to enforce the PR portion of that policy.
These files do not configure protection rules or create/merge PRs automatically.
A direct push to `main`, if repository settings permit one, is still a main push
and can trigger packaging after checks; do not use it to bypass review.

## Workflows and local verification

- [Product checks](../../.github/workflows/checks.yml): pre-merge/source checks.
- [Packages after merge](../../.github/workflows/packages.yml): post-merge artifacts.
- `tests/unit/test_ci_policy.py`: regression checks for that separation, exact
  source checkout and trusted-main event guards.

For branch review, run `python3 tools/check-product.py`. On Debian/Ubuntu the
native archive test remains skipped unless explicitly opted in with
`PBI_PACKAGE_BUILD_TESTS=1`; reserve that opt-in for post-merge package validation.
`tools/build-deb.py --stage-only /path/to/new-directory` is allowed for metadata
inspection without producing a DEB. Do not build new RPM/DEB archives during PR
review. The manual commands in [Build](build.md) document post-merge reproduction.

Source RPMs include `.github` and `.gitignore` so source checks and export tools
remain available when rebuilding from them. The application runtime is not rebuilt
by this package pipeline, and no Microsoft installer or real report is executed.

## Security and scope

`workflow_run` is deliberately limited to successful same-repository main-push
checks. Checkout uses their exact SHA and does not persist credentials. Packaging
has read-only repository permissions and does not download untrusted PR artifacts.
Do not weaken those guards to make a feature-branch package build run.

Container checks do not certify Wayland input, Vulkan, sign-in, report correctness
or prolonged Desktop sessions. Fedora remains the tested baseline and the DEB
platforms remain experimental. No resource preset or snapshot policy is changed
by the delivery workflows.
