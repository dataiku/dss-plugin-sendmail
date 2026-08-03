# Cobuild guidance

- For the sender, either set `sender_column`, or set `use_sender_value=true` and `sender_value`, unless the selected mail channel already defines the sender.
- For the subject, either set `subject_column`, or set `use_subject_value=true` and `subject_value`.
- For the body, either set `body_column`, or set `use_body_value=true` and use `body_format` with `body_value` for plain text or `html_body_value` for HTML.
- For `mail_channel`, call the `list_message_channels` tool with `integrationType=mail`. If several channels are available and the user did not identify one, ask which one to use.
- Set `mail_channel` to the chosen channel id. Append `__WITH_DEFINED_SENDER__` when its `sender` is set or `useCurrentUserAsSender` is true.
- If the user chooses to configure SMTP directly instead of using a DSS mail channel, set `mail_channel` to `__DKU__DIRECT_SMTP__`. When no DSS mail channel exists, leave it null.
