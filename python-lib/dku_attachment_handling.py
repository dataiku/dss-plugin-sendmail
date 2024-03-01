from dku_email_client import AttachmentFile


def attachments_template_dict(attachment_datasets):
    """
     :param attachments_datasets: List of attachment datasets (DSS datasets)
     :return dictionary of attachment dataset nams each to a dict containing keys `html_table` and `data`,
             where `data` is a list of records, each a dictionary of column names to values,
             and `html_table` is a string of html for the table with css class `dataframe`
             Only the first 50 rows are included.
    """

    attachments_dict = {}
    for attachment_ds in attachment_datasets:
        table_df = attachment_ds.get_dataframe().head(50)

        attachment_entry = attachments_dict[attachment_ds.full_name.split('.')[1]] = {}
        attachment_entry["html_table"] = table_df.to_html(index=False, justify='left', border=0, na_rep="")
        attachment_entry["data"] = table_df.to_dict('records')

    return attachments_dict


def build_attachment_files(attachment_datasets, attachment_type):
    """
        :param attachment_datasets: List of attachment datasets
        :param attachment_type: str, e.g. "excel", "csv"
        :return: Attachments as List of AttachmentFile
    """

    if attachment_type == "excel":
        request_fmt = "excel"
    else:
        request_fmt = "tsv-excel-header"

    # Prepare attachments
    attachment_files = []
    for attachment_ds in attachment_datasets:
        with attachment_ds.raw_formatted_data(format=request_fmt) as stream:
            file_bytes = stream.read()
        if attachment_type == "excel":
            attachment_files.append(AttachmentFile(attachment_ds.full_name + ".xlsx", "application",
                                                     "vnd.openxmlformats-officedocument.spreadsheetml.sheet", file_bytes))
        else:
            attachment_files.append(AttachmentFile(attachment_ds.full_name + ".csv", "text", "csv", file_bytes))
    return attachment_files
