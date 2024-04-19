# Changelog

## [Version 1.0.1](https://github.com/dataiku/dss-plugin-sendmail/releases/tag/v1.0.1) - Feature release - 2024-04

- Recipe configurations saved in version 1.0.0 with "Attachments format" set to "Nothing selected" will no longer send CSV attachments.
  If you send CSV attachments in your integrations, please check existing recipes before upgrading to ensure they explicitly use the CSV option.

- Features added
  - Generate HTML tables where colors from conditional formatting are applied for inline datasets

## [Version 1.0.0](https://github.com/dataiku/dss-plugin-sendmail/releases/tag/v1.0.0) - Feature release - 2024-02

- REMOVED SUPPORT FOR PYTHON 2.7 AND 3.5. The code env used must be in range python 3.6 - 3.11 inclusive

- Features added
  - Templating capabilities - use JINJA style templating in the email body and subject line
  - Send as HTML
  - Ability to use DSS channels to send emails

## [Version 0.2.0](https://github.com/dataiku/dss-plugin-sendmail/releases/tag/v0.2.0) - Feature release - 2023-08

- Added support for python versions 3.8, 3.9, 3.10 and 3.11 (DSS-12)

## [Version 0.1.9](https://github.com/dataiku/dss-plugin-sendmail/releases/tag/v0.1.9) - Feature release - 2023-08

- Added ability to turn on TLS and to specify user + pass
