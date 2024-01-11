from email.mime.application import MIMEApplication
from email.mime.text import MIMEText


def attachments_template_dict(attachment_datasets):
    """
     :param attachments: List of attachment datasets
     :return dictionary of attachment dataset nams each to a dict containing keys `html_table` and `data`,
             where `data` is a list of records, each a dictionary of column names to values,
             and `html_table` is a string of html for the table with css class `dataframe`
             Only the first 50 rows are included.
    """

    attachments_dict = {}
    for attachment_ds in attachment_datasets:
        table_df = attachment_ds.get_dataframe().head(50)

        attachment_entry = attachments_dict[attachment_ds.full_name.split('.')[1]] = {}
        attachment_entry["html_table"] = table_df.to_html(index=False, justify='left')
        attachment_entry["data"] = table_df.to_dict('records')

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
