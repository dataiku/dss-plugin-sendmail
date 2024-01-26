import dataiku
from dataiku.customrecipe import get_output_names_for_role, get_input_names_for_role, get_recipe_config
import logging
from email_client import SmtpConfig, SmtpEmailClient, ChannelClient
from dss_selector_choices import SENDER_SUFFIX
from attachment_handling import build_attachment_files, attachments_template_dict
from jinja2 import Environment, StrictUndefined

jinja_env = Environment(undefined=StrictUndefined)


def read_smtp_config(recipe_config):
    """ Extract SmtpConfig (named tuple) from recipe_config dict """

    smtp_host = recipe_config.get('smtp_host', None)
    smtp_port = int(recipe_config.get('smtp_port', "25"))
    smtp_use_tls = recipe_config.get('smtp_use_tls', False)
    smtp_use_auth = recipe_config.get('smtp_use_auth', False)
    smtp_user = recipe_config.get('smtp_user', None)
    smtp_pass = recipe_config.get('smtp_pass', None)
    return SmtpConfig()(smtp_host, smtp_port, smtp_use_tls, smtp_use_auth, smtp_user, smtp_pass)


def to_real_channel_id(channel_id):
    # Remove suffix added in dynamic_channels when the channel has a sender
    if channel_id.endswith(SENDER_SUFFIX):
        return channel_id[:-len(SENDER_SUFFIX)]
    else:
        return channel_id


def does_channel_have_sender(channel_id):
    return channel_id is not None and channel_id.endswith(SENDER_SUFFIX)


def send_email_for_contact(mail_client, contacts_row, message_template):
    """
    Send an email with the relevant data for the contacts_row and given template
    :param mail_client: SmtpEmailClient
    :param contacts_row: dict
    :param message_template: jinja Template|None - email template or None if this the message is provided in the row data
    Sends the message or throws an exception
    """

    recipient = contacts_row[recipient_column]
    email_subject = subject_value if use_subject_value else contacts_row.get(subject_column, "")

    if use_body_value:
        if message_template:
            templating_value_dict = dict(contacts_row)

            if "attachments" in templating_value_dict:
                # If there is column in the contacts dataset called "attachments" that takes priority, but we log a warning
                logging.warning("The input (contacts) dataset contains a column called 'attachments'. "
                             "If you want to display attachments data with the variable 'attachments' that column will have to be renamed")
            else:
                # Normal case - make attachments data available for JINJA
                templating_value_dict["attachments"] = attachments_templating_dict

            if "subject" in templating_value_dict:
                # If there is column in the contacts dataset called "subject" that takes priority, but we log a warning
                logging.warning("The input (contacts) dataset contains a column called 'subject'. "
                                "If you want to display the email subject as a variable in the template, that column will have to be renamed")
            else:
                # Normal case - make attachments data available for JINJA
                templating_value_dict["subject"] = email_subject

            try:
                email_text = message_template.render(templating_value_dict)
            except Exception as exp:
                raise Exception("Could not render template: {} ".format(exp))
        else:
            raise Exception("No template was generated to use for the message")
    else:
        email_text = contacts_row.get(body_column, "")


    # Note -  if the channel has a sender configured, the sender value will be ignored by the email client
    sender = sender_value if use_sender_value else contacts_row.get(sender_column, "")
    mail_client.send_email(sender, recipient, email_subject, email_text, attachment_files)


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Get handles on datasets
output_A_names = get_output_names_for_role('output')
output = dataiku.Dataset(output_A_names[0]) if len(output_A_names) > 0 else None

people = dataiku.Dataset(get_input_names_for_role('contacts')[0])
attachment_datasets = [dataiku.Dataset(x) for x in get_input_names_for_role('attachments')]

# Read configuration
config = get_recipe_config()

recipient_column = config.get('recipient_column', None)

sender_column = config.get('sender_column', None)
sender_value = config.get('sender_value', None)
use_sender_value = config.get('use_sender_value', False)

subject_column = config.get('subject_column', None)
subject_value = config.get('subject_value', None)
use_subject_value = config.get('use_subject_value', False)

use_body_value = config.get('use_body_value', False)

body_column = config.get('body_column', None)
body_value = config.get('body_value', None)

# For legacy configs, assume it is text if not defined
body_format = config.get('body_format', 'text')
# For sending a body from a column value we also assume it is plain text - that is the legacy behavour
use_html_body_value = body_value and (body_format == 'html')

html_body_value = config.get('html_body_value', None)
mail_channel = config.get('mail_channel', None)
channel_has_sender = does_channel_have_sender(mail_channel)

if mail_channel is None:
    smtp_config = read_smtp_config(config)

attachment_type = config.get('attachment_type', "csv")

# Check some kind of value/column exists for body, subject, sender

if not body_column and not (use_body_value and body_value) and not (use_html_body_value and html_body_value):
    raise AttributeError("No body column nor body value specified")

if not subject_column and not (use_subject_value and subject_value):
    raise AttributeError("No value provided for the subject")

if not sender_column and not channel_has_sender and not (use_subject_value and sender_value):
    raise AttributeError("No value provided for the sender")

# When necessary, check the column values provided are in the contacts (people) dataset
people_columns = [p['name'] for p in people.read_schema()]
for arg in ['subject', 'body']:
    if not globals()["use_" + arg + "_value"] and globals()[arg + "_column"] not in people_columns:
        raise AttributeError("The column you specified for %s (%s) was not found." % (arg, globals()[arg + "_column"]))

if not use_sender_value and not channel_has_sender and sender_column not in people_columns:
    raise AttributeError("The column you specified for %s (%s) was not found." % ("sender", sender_column))


body_template = None
if use_body_value:
    if use_html_body_value:
        body_template = jinja_env.from_string(html_body_value)
    else:
        body_template = jinja_env.from_string(body_value)

# Write schema
output_schema = list(people.read_schema())
output_schema.append({'name': 'sendmail_status', 'type': 'string'})
output_schema.append({'name': 'sendmail_error', 'type': 'string'})
output.write_schema(output_schema)

attachment_files = build_attachment_files(attachment_datasets, attachment_type)

attachments_templating_dict = attachments_template_dict(attachment_datasets)

if mail_channel is None:
    email_client = SmtpEmailClient(not use_html_body_value, smtp_config)
else:
    email_client = ChannelClient(not use_html_body_value, to_real_channel_id(mail_channel))

with output.get_writer() as writer:
    i = 0
    success = 0
    fail = 0
    try:
        for contact in people.iter_rows():
            logging.info("Sending to %s" % contact)
            try:
                send_email_for_contact(email_client, contact, body_template)
                d = dict(contact)
                d['sendmail_status'] = 'SUCCESS'
                success += 1
                if writer:
                    writer.write_row_dict(d)
            except Exception as e:
                logging.exception("Send failed")
                fail += 1
                d = dict(contact)
                d['sendmail_status'] = 'FAILED'
                d['sendmail_error'] = str(e)
                if writer:
                    writer.write_row_dict(d)
            i += 1
            if i % 5 == 0:
                logging.info("Sent %d mails (%d success %d fail)" % (i, success, fail))
    except RuntimeError as runtime_error:
        # https://stackoverflow.com/questions/51700960/runtimeerror-generator-raised-stopiteration-every-time-i-try-to-run-app
        logging.info("Exception {}".format(runtime_error))
email_client.quit()
