from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
import dataiku

def do(payload, config, plugin_config, inputs):

    parameter_name = payload.get("parameterName")
    if parameter_name == "mail_channel":
        choices = DSSSelectorChoices()
        dss_client = dataiku.api_client()
        channels = []
        # To work for < 12.6 DSS - first check API to list channels exists, only call it if it does
        if callable(getattr(dss_client, "list_integration_channels", None)):
            channels = dss_client.list_integration_channels()
        for channel in channels:
            if 'smtp' in channel.get('type') or 'mail' in channel.get('type'):
                if channel.get('sender'):
                    # If the channel has a sender append `(<sender email>)` to label and `_S` flag to channel ID
                    choices.append(f"{channel.get('id')} ({channel.get('sender')})", channel.get('id') + SENDER_SUFFIX)
                else:
                    choices.append(f"{channel.get('id')}",  channel.get('id'))

        # Add an entry for direct SMTP
        if len(channels) > 0:
            # If there is a choice of channels, giving direct SMTP a key of "direct_smtp" means it is there but not as default
            choices.append("Manually define SMTP", 'direct_smtp')
        else:
            # If there is no choice, put SMTP there but with a key of None, so it will be the default instead of "Nothing selected"
            choices.append("Manually define SMTP", None)

        return choices.to_dss()
