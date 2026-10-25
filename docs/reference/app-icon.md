# Original Power BI desktop icon

User integration extracts the original PNG from the icon group in the installed
`PBIDesktop.exe`. The pinned application provides a 512×512 PNG; those exact bytes
are retained, without redrawing the logo. The desktop entry references the
extracted file directly, preserving the launcher and file associations.

Setup/repair installs it, and opening through RPM 11 refreshes existing user
integration after an upgrade or profile change. A source/icon hash record avoids
unnecessary rewriting. Uninstall removes the generated user artwork and record.
The RPM's generic fallback remains available before Power BI is provisioned or
when the application's icon format cannot be read. An artwork failure does not
prevent opening a report.

Microsoft artwork is extracted only for the user's local installation; it is not
bundled in the public source tree or RPM. The extractor uses Python's standard
library and validates PE/resource bounds and PNG chunk checksums. No Wine process,
network request or additional image-processing package is required for this step.
