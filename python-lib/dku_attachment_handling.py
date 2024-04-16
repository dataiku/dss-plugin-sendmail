from dku_email_client import AttachmentFile
import logging


def attachments_template_dict(attachment_datasets, home_project_key):
    """
     :param attachment_datasets: List of attachment datasets (DSS datasets)
     :param home_project_key: key of the project we are in
     :return dictionary of attachment dataset nams each to a dict containing keys `html_table` and `data`,
             where `data` is a list of records, each a dictionary of column names to values,
             and `html_table` is a string of html for the table with css class `dataframe`
             Only the first 50 rows are included.
    """

    attachments_dict = {}
    for attachment_ds in attachment_datasets:
        table_df = attachment_ds.get_dataframe(limit=50)
        ds_name = attachment_ds.full_name.split(".")[1]
        if attachment_ds.project_key == home_project_key:
            attachment_entry = attachments_dict.setdefault(ds_name, {})
        else:
            # For foreign datasets, we need another level in the map with the
            ext_project_entry = attachments_dict.setdefault(attachment_ds.project_key, {})
            attachment_entry = ext_project_entry.setdefault(ds_name, {})

        # Use DSS to_html method if available (DSS 12.6.2+)
        if hasattr(attachment_ds.__class__, "to_html") and callable(getattr(attachment_ds.__class__, "to_html")):
            attachment_entry["html_table"] = attachment_ds.to_html(limit=50, border=0, null_string="")
        else:
            attachment_entry["html_table"] = table_df.to_html(index=False, justify='left', border=0, na_rep="")
        attachment_entry["data"] = table_df.to_dict('records')

    return attachments_dict


def build_attachment_files(attachment_datasets, attachment_type, apply_coloring_excel):
    """
        :param attachment_datasets: List of attachment datasets
        :param attachment_type: str, e.g. "excel", "csv" - "excel_can_ac" is treated as excel
        :param apply_coloring_excel: boolean, whether to apply conditional formatting (aka coloring) for Excel attachments
        :return: Attachments as List of AttachmentFile
    """
    logging.info(f"Building attachments, type: {attachment_type}, apply colouring? {apply_coloring_excel}")
    is_excel = attachment_type == "excel" or attachment_type == "excel_can_ac"

    format_params = None
    if is_excel:
        request_fmt = "excel"
        if apply_coloring_excel and attachment_type == "excel_can_ac":
            format_params = {"applyColoring": True}
    else:
        request_fmt = "tsv-excel-header"

    # Prepare attachments
    attachment_files = []
    for attachment_ds in attachment_datasets:
        with attachment_ds.raw_formatted_data(format=request_fmt, format_params=format_params) as stream:
            file_bytes = stream.read()
        if is_excel:
            attachment_files.append(AttachmentFile(attachment_ds.full_name + ".xlsx", "application",
                                                     "vnd.openxmlformats-officedocument.spreadsheetml.sheet", file_bytes))
        else:
            attachment_files.append(AttachmentFile(attachment_ds.full_name + ".csv", "text", "csv", file_bytes))
    return attachment_files
