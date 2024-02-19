from dss_selector_choices import DSSSelectorChoices, SENDER_SUFFIX
import dataiku


def is_12_6_plus(dss_client):
    # Check for existance of messaging channel API we added in 12.6
    return callable(getattr(dss_client, "list_messaging_channels", None))


def do(payload, config, plugin_config, inputs):
    dss_client = dataiku.api_client()
    parameter_name = payload.get("parameterName")

    if parameter_name == "mail_channel":
        choices = DSSSelectorChoices()
        channels = []
        if is_12_6_plus(dss_client):
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
            choices.append("Manually define SMTP", "direct_smtp")
        else:
            # If there is no choice, put SMTP there but with a key of None, so it will be the default instead of "Nothing selected"
            choices.append("Manually define SMTP", None)
        return choices.to_dss()

    if parameter_name == "attachment_type":
        choices = DSSSelectorChoices()
        if is_12_6_plus(dss_client):
            # Added excel and give it the key excel_can_ac to indicate to the UI that we can show the
            # apply coloring ("apply conditional formatting") option
            choices.append("Excel", "excel_can_ac")
        else:
            choices.append("Excel", "excel")
        choices.append("CSV", "csv")
        return choices.to_dss()
