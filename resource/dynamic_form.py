from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
from dku_support_detection import supports_messaging_channels_and_conditional_formatting
from jinja2 import ChainableUndefined, Environment
import dataiku

EMAIL_TEMPLATE_PREVIEW_CALLBACK = "preview_email_body"

class SampleUndefined(ChainableUndefined):
    def __str__(self):
        return "Example"

    def __iter__(self):
        yield self
        yield self

    def __len__(self):
        return 2

    def __bool__(self):
        return True


jinja_env = Environment(undefined=SampleUndefined)


def preview_email_body(payload):
    try:
        rendered_html = jinja_env.from_string(payload["html"]).render()
    except Exception as e:
        return {"error": str(e)}

    return {"html": rendered_html}

def do(payload, config, plugin_config, inputs):
    if payload.get("templatePreviewCallback") == EMAIL_TEMPLATE_PREVIEW_CALLBACK:
        return preview_email_body(payload)

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

    return {}
