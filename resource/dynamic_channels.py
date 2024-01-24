from dss_selector_choices import DSSSelectorChoices
import dataiku


def do(payload, config, plugin_config, inputs):
    choices = DSSSelectorChoices()
    dss_client = dataiku.api_client()
    channels = dss_client.list_integration_channels()
    for channel in channels:
        if 'smtp' in channel.get('type') or 'mail' in channel.get('type'):
            channel_label = f"Channel: {channel.get('id')}"
            if channel.get('sender'):
                channel_label = channel_label + f" ({channel.get('sender')})"
            choices.append(channel_label, channel.get('id'))
    choices.append("Manually define SMTP", None)
    return choices.to_dss()
