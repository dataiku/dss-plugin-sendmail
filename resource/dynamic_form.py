from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
from dku_support_detection import supports_messaging_channels_and_conditional_formatting
import dataiku


def do(payload, config, plugin_config, inputs):
    dss_client = dataiku.api_client()
    parameter_name = payload.get("parameterName")

    if parameter_name == "mail_channel":
        choices = DSSSelectorChoices()
        channels = []
        if supports_messaging_channels_and_conditional_formatting(dss_client):
            channels = dss_client.list_messaging_channels(as_type="objects", channel_family="mail")
        for channel in channels:
            if channel.sender:
                # If the channel has a sender append `(<sender email>)` to label and SENDER_SUFFIX flag to channel ID
                choices.append(f"{channel.id} ({channel.sender})", channel.id + SENDER_SUFFIX)
            else:
                choices.append(f"{channel.id}",  channel.id)

        # Add an entry for direct SMTP
        if len(channels) > 0:
            # If there is a choice of channels, giving direct SMTP a key of "__DKU__DIRECT_SMTP__" means it is there but not as default
            choices.append("Manually define SMTP", "__DKU__DIRECT_SMTP__")
        else:
            # If there is no choice, put SMTP there but with a key of None, so it will be the default instead of "Nothing selected"
            choices.append("Manually define SMTP", None)
        return choices.to_dss()
