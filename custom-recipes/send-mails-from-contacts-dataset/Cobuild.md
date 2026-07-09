# Cobuild guidance

Use this recipe to send one email per row of the contacts dataset. It can also include optional attachment datasets and writes send status rows to the optional output dataset.

Roles:
- `contacts`: required input dataset. It must contain the recipient column and any columns used by sender, subject, body templates, or Jinja variables.
- `attachments`: optional input datasets. Use when the email body or attachment files need data from extra datasets.
- `output`: optional output dataset for send status. Create or select it when the user wants delivery status persisted.

Core configuration:
- Set `recipient_column` to the email-recipient column from `contacts`.
- For the sender, either set `sender_column`, or set `use_sender_value=true` and `sender_value`, unless the selected mail channel already defines the sender.
- For the subject, either set `subject_column`, or set `use_subject_value=true` and `subject_value`.
- For the body, either set `body_column`, or set `use_body_value=true` and use `body_format` with `body_value` for plain text or `html_body_value` for HTML.
- `body_value` and `html_body_value` support Jinja templating over columns from the contacts dataset and attached datasets.
- Set `attachment_type` to `send_no_attachments`, `excel`, or `csv`.

Mail channel handling:
- `mail_channel` is a dynamic choice. Use `list_message_channels` with `integrationType=mail` to discover mail channels.
- If using a listed channel, set `mail_channel` to the channel id.
- If the channel has a configured sender or uses the current user as sender, append `__WITH_DEFINED_SENDER__` to the channel id.
- If using direct SMTP, set `mail_channel` to `__DKU__DIRECT_SMTP__` when channels exist, or leave it null when direct SMTP is the only option.

Direct SMTP configuration:
- When `mail_channel` is null or `__DKU__DIRECT_SMTP__`, set `smtp_host` and `smtp_port`.
- Set `smtp_use_tls` when TLS is required.
- If SMTP authentication is required, set `smtp_use_auth=true` and `smtp_user`.
- Do not ask the user to paste `smtp_pass` in chat. Create the recipe, navigate to the recipe settings, and ask the user to fill the password there.
