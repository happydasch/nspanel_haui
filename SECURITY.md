# Security Policy

## Supported versions

Only the latest stable release receives security fixes. Development builds (`X.Y.Z.devN`) and older releases
are not supported.

Keep the integration, the panel firmware and the display TFT updated. The editor offers all three, and updates
install together.

## Reporting a vulnerability

Do not report security problems in a public issue, discussion or community thread.

Use GitHub's [private vulnerability reporting](https://github.com/happydasch/nspanel_haui/security/advisories/new)
and include:

- what is affected: the integration, the firmware, the display assets or the editor;
- the versions involved;
- the impact, and steps to reproduce or a proof of concept.

This is a volunteer-maintained project, so reports are handled on a best-effort basis. A fix ships in a stable
release and the advisory credits the reporter unless they prefer otherwise.

## Scope

In scope:

- the integration in `custom_components/nspanel_haui/`, including the admin API and the editor;
- the ESPHome configuration and components in `esphome/`;
- the Nextion HMI and TFT assets in `nextion/`;
- the release and update tooling in `scripts/` and `.github/`.

Out of scope:

- vulnerabilities in Home Assistant, ESPHome, the Nextion display firmware or Home Assistant itself;
  report those to the respective project;
- the public API key and open access point of the universal firmware image. They are documented trade-offs
  of the no-YAML install path; use a custom build for private credentials;
- a panel whose owner deliberately opened its editor or API to an untrusted network.

## Protect your data

Never post passwords, Wi-Fi credentials, API keys or access tokens in an issue or discussion. The editor's
**Copy report** includes versions and diagnostics, not secrets; check it before posting anyway.
