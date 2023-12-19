from email.mime.application import MIMEApplication
from email.mime.text import MIMEText


def attachments_to_html(attachment_datasets):
    # data structure to pass to jinja
    attachments_dict = {}

    for attachment_ds in attachment_datasets:
        df = attachment_ds.get_dataframe()
        attachment_entry = attachments_dict[attachment_ds.full_name.split('.')[1]] = {}
        attachment_entry["html_table"] = df.to_html()

    return attachments_dict


def build_attachments(attachments, attachment_type):
    """
    :param attachments: List of attachment datasets
    :param attachment_type: str, e.g. "excel", "csv"
    :return: Attachments as List of MIMEApplication
    """

    # Prepare attachments
    mime_parts = []
    for a in attachments:

        if attachment_type == "excel":
            request_fmt = "excel"
        else:
            request_fmt = "tsv-excel-header"
            filename = a.full_name + ".csv"
            mimetype = ["text", "csv"]

        with a.raw_formatted_data(format=request_fmt) as stream:
            buf = stream.read()

        if attachment_type == "excel":
            app = MIMEApplication(buf, _subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            app.add_header("Content-Disposition", 'attachment', filename=a.full_name + ".xlsx")
            mime_parts.append(app)
        else:
            txt = MIMEText(buf, _subtype="csv", _charset="utf-8")
            txt.add_header("Content-Disposition", 'attachment', filename=a.full_name + ".csv")
            mime_parts.append(txt)
    return mime_parts
