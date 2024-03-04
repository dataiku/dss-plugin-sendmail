import logging


def build_email_subject(use_subject_value, subject_line_template, subject_column, contact_dict):
    if use_subject_value:
        if subject_line_template:
            try:
                email_subject = subject_line_template.render(contact_dict)
            except Exception as exp:
                raise Exception("Could not render subject template: {} ".format(exp))
        else:
            raise Exception("No template was generated to use for the subject")
    else:
        email_subject = contact_dict.get(subject_column, "")
    return email_subject


def build_email_message_text(use_body_value, message_template, attachments_templating_dict, contact_dict, body_column, use_html_body_value):
    if use_body_value:
        if message_template:
            templating_value_dict = contact_dict.copy()
            if "attachments" in templating_value_dict:
                # If there is column in the contacts dataset called "attachments" that takes priority, but we log a warning
                logging.warning("The input (contacts) dataset contains a column called 'attachments'. "
                                "If you want to display attachments data with the variable 'attachments' that column will have to be renamed")
            else:
                # Normal case - make attachments data available for JINJA
                templating_value_dict["attachments"] = attachments_templating_dict
            try:
                email_text = message_template.render(templating_value_dict)
            except Exception as exp:
                raise Exception("Could not render body template: {} ".format(exp))
        else:
            raise Exception("No template was generated to use for the message")
    else:
        email_text = contact_dict.get(body_column, "")

    if not use_html_body_value:
        # To make sure there is a gap before attachments (TBH I'm not sure it is necessary or does much, just maintaining consistency with legacy behaviour)
        email_text = email_text + '\n\n'

    return email_text
