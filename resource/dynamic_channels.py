from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
import dataiku

def do(payload, config, plugin_config, inputs):

    parameter_name = payload.get("parameterName")
    if parameter_name == "mail_channel":
        choices = DSSSelectorChoices()
        dss_client = dataiku.api_client()
        channels = []
        # To work for < 12.6 DSS - first check API to list channels exists, only call it if it does
        if callable(getattr(dss_client, "list_messaging_channels", None)):
            channels = dss_client.list_messaging_channels(as_type="objects", channel_family="mail")
        for channel in channels:
            if channel.sender:
                # If the channel has a sender append `(<sender email>)` to label and SENDER_SUFFIX flag to channel ID
                choices.append(f"{channel.id} ({channel.sender})", channel.id + SENDER_SUFFIX)
            else:
                choices.append(f"{channel.id}",  channel.id)

        # Add an entry for direct SMTP
        if len(channels) > 0:
            # If there is a choice of channels, giving direct SMTP a key of "direct_smtp" means it is there but not as default
            choices.append("Manually define SMTP", 'direct_smtp')
        else:
            # If there is no choice, put SMTP there but with a key of None, so it will be the default instead of "Nothing selected"
            choices.append("Manually define SMTP", None)

        return choices.to_dss()
