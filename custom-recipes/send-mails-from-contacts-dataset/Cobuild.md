# Cobuild guidance

Role-specific behavior:
- `contacts` supplies recipients and the columns available to sender, subject, body, and Jinja templates.
- `attachments` supplies additional datasets used in templates or generated attachments.
- `output`, when configured, persists delivery-status rows that should be reviewed even when the recipe run succeeds.

Message configuration:
- For the sender, either set `sender_column`, or set `use_sender_value=true` and `sender_value`, unless the selected mail channel already defines the sender.
- For the subject, either set `subject_column`, or set `use_subject_value=true` and `subject_value`.
- For the body, either set `body_column`, or set `use_body_value=true` and use `body_format` with `body_value` for plain text or `html_body_value` for HTML.
- `body_value` and `html_body_value` support Jinja templating over columns from the contacts dataset and attached datasets.

Mail channel handling:
- `mail_channel` is a dynamic choice. Use `list_message_channels` with `integrationType=mail` to discover mail channels.
- If using a listed channel, set `mail_channel` to the channel id.
- If the channel has a configured sender or uses the current user as sender, append `__WITH_DEFINED_SENDER__` to the channel id.
- If using direct SMTP, set `mail_channel` to `__DKU__DIRECT_SMTP__` when channels exist, or leave it null when direct SMTP is the only option.
