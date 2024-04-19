# Functions to determine if features in the DSS API are supported

def supports_dataset_to_html(dataset):
    # Check for existence to_html() method we added in 12.6.2
    return hasattr(dataset.__class__, "to_html") and callable(getattr(dataset.__class__, "to_html"))


