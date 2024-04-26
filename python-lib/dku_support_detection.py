# Functions to determine if features in the DSS API are supported

def supports_dataset_to_html(dataset):
    # Check for existence to_html() method we added in 12.6.2
    return hasattr(dataset.__class__, "to_html") and callable(getattr(dataset.__class__, "to_html"))

def supports_messaging_channels_and_conditional_formatting(dss_client):
    # Check for existence of messaging channel API we added in 12.6
    # If this is here we also support conditional formatting, as this was done in the same version
    return callable(getattr(dss_client, "list_messaging_channels", None))
