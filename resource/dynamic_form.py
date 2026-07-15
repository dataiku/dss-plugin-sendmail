from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
from dku_support_detection import supports_messaging_channels_and_conditional_formatting
from jinja2 import Environment, StrictUndefined
from dku_attachment_handling import attachments_template_dict
from email_utils import build_email_message_text
import dataiku

EMAIL_TEMPLATE_PREVIEW_CALLBACK = "preview_email_body"

jinja_env = Environment(undefined=StrictUndefined)


def _input_names_for_role(inputs, role):
    return [
        input_desc.get("fullName")
        for input_desc in (inputs or [])
        if input_desc.get("role") == role and input_desc.get("fullName")
    ]


def _first_row(dataset):
    for row in dataset.iter_rows():
        return dict(row)
    return None


def preview_email_body(payload, config, inputs):
    html = payload.get("html") or ""

    contact_names = _input_names_for_role(inputs, "contacts")
    if not contact_names:
        return {"html": html}

    people = dataiku.Dataset(contact_names[0])
    contact_dict = _first_row(people)
    if contact_dict is None:
        return {"html": html}

    attachment_datasets = [
        dataiku.Dataset(dataset_name)
        for dataset_name in _input_names_for_role(inputs, "attachments")
    ]

    try:
        attachments_templating_dict = attachments_template_dict(
            attachment_datasets,
            dataiku.default_project_key(),
            (config or {}).get("apply_coloring_excel", False),
        )
        body_template = jinja_env.from_string(html)
        rendered_html = build_email_message_text(
            True,
            body_template,
            attachments_templating_dict,
            contact_dict,
            None,
            True,
        )
    except Exception as e:
        return {"html": html, "error": str(e)}

    return {"html": rendered_html}

def do(payload, config, plugin_config, inputs):
    dss_client = dataiku.api_client()
    parameter_name = payload.get("parameterName")

    if parameter_name == "mail_channel":
        choices = DSSSelectorChoices()
        channels = []
        if supports_messaging_channels_and_conditional_formatting(dss_client):
            channels = dss_client.list_messaging_channels(as_type="objects", channel_family="mail")
        for channel in channels:
            if 'use_current_user_as_sender' in dir(channel) and channel.use_current_user_as_sender:
                # If the channel has a locked-down sender using current user, append `(user email)` to label and SENDER_SUFFIX flag to channel ID
                choices.append(f"{channel.id} (user email)", channel.id + SENDER_SUFFIX)
            elif channel.sender:
                # If the channel has a sender append `(<sender email>)` to label and SENDER_SUFFIX flag to channel ID
                choices.append(f"{channel.id} ({channel.sender})", channel.id + SENDER_SUFFIX)
            else:
                choices.append(f"{channel.id}", channel.id)

                # Add an entry for direct SMTP
        if len(channels) > 0:
            # If there is a choice of channels, giving direct SMTP a key of "__DKU__DIRECT_SMTP__" means it is there but not as default
            choices.append("Manually define SMTP", "__DKU__DIRECT_SMTP__")
        else:
            # If there is no choice, put SMTP there but with a key of None, so it will be the default instead of "Nothing selected"
            choices.append("Manually define SMTP", None)
        return choices.to_dss()

    if payload.get("templatePreviewCallback") == EMAIL_TEMPLATE_PREVIEW_CALLBACK:
        return preview_email_body(payload, config, inputs)

    return {}
