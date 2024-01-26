from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
import dataiku

def do(payload, config, plugin_config, inputs):
    choices = DSSSelectorChoices()
    dss_client = dataiku.api_client()
    channels = dss_client.list_integration_channels()
    for channel in channels:
        if 'smtp' in channel.get('type') or 'mail' in channel.get('type'):
            if channel.get('sender'):
                # If the channel has a sender append `(<sender email>)` to label and `_S` flag to channel ID
                choices.append(f"Channel: {channel.get('id')} ({channel.get('sender')})", channel.get('id') + SENDER_SUFFIX)
            else:
                choices.append(f"Channel: {channel.get('id')}",  channel.get('id'))

    choices.append("Manually define SMTP", None)
    return choices.to_dss()
