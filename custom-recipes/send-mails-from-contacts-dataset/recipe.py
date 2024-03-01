import dataiku
from dataiku.customrecipe import get_output_names_for_role, get_input_names_for_role, get_recipe_config
import logging
from dku_email_client import SmtpConfig, SmtpEmailClient, ChannelClient
from dss_selector_choices import SENDER_SUFFIX
from dku_attachment_handling import build_attachment_files, attachments_template_dict
from jinja2 import Environment, StrictUndefined

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

jinja_env = Environment(undefined=StrictUndefined)

def read_smtp_config(recipe_config):
    """ Extract SmtpConfig (named tuple) from recipe_config dict """

    smtp_host = recipe_config.get('smtp_host', None)
    smtp_port = int(recipe_config.get('smtp_port', "25"))
    smtp_use_tls = recipe_config.get('smtp_use_tls', False)
    smtp_use_auth = recipe_config.get('smtp_use_auth', False)
    smtp_user = recipe_config.get('smtp_user', None)
    smtp_pass = recipe_config.get('smtp_pass', None)
    return SmtpConfig(smtp_host, smtp_port, smtp_use_tls, smtp_use_auth, smtp_user, smtp_pass)


def to_real_channel_id(channel_id):
    # Remove suffix added in dynamic_channels when the channel has a sender
    if channel_id.endswith(SENDER_SUFFIX):
        return channel_id[:-len(SENDER_SUFFIX)]
    else:
        return channel_id


def does_channel_have_sender(channel_id):
    return channel_id is not None and channel_id.endswith(SENDER_SUFFIX)


def send_email_for_contact(mail_client, contact_dict, message_template, subject_line_template):
    """
    Send an email with the relevant data for the contacts_row and given template
    :param mail_client: SmtpEmailClient
    :param contact_dict: dict
    :param message_template: jinja Template|None - email template or None if this the message is provided in the row data
    :param subject_line_template: jinja Template|None - subject line template or None if this the subject is provided in the row data
    Sends the message or throws an exception
    """

    recipient = contact_dict[recipient_column]
    # What is sent to templating is different from what we want to write iin the outputrg
    templating_value_dict = contact_dict.copy()

    if use_subject_value:
        if subject_line_template:
            # Render subject before we add attachments as these wouldn't make sense in the subject line
            try:
                email_subject = subject_line_template.render(templating_value_dict)
            except Exception as exp:
                raise Exception("Could not render subject template: {} ".format(exp))
        else:
            raise Exception("No template was generated to use for the subject")
    else:
        email_subject = contact_dict.get(subject_column, "")

    if use_body_value:
        if message_template:
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

    # Note - if the channel has a sender configured, the sender value will be ignored by the email client here
    sender = sender_value if use_sender_value else contact_dict.get(sender_column, "")
    mail_client.send_email(sender, recipient, email_subject, email_text, attachment_files)




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
use_html_body_value = use_body_value and (body_format == 'html')

html_body_value = config.get('html_body_value', None)
mail_channel = config.get('mail_channel', None)
channel_has_sender = does_channel_have_sender(mail_channel)

attachment_type = config.get('attachment_type', "csv")

# Validation part 1 - Check some kind of value/column exists for body, subject, sender and recipient

has_body_column = body_column and not use_body_value
has_plain_body_value = use_body_value and body_value and not use_html_body_value
has_html_body_value = use_body_value and use_html_body_value and html_body_value
if not (has_body_column or has_plain_body_value or has_html_body_value):
    raise AttributeError("No body column nor body value specified")

has_subject_column = subject_column and not use_subject_value
has_subject_value = use_subject_value and subject_value
if not has_subject_column and not has_subject_value:
    raise AttributeError("No value provided for the subject")

has_sender_column = sender_column and not use_sender_value and not channel_has_sender
has_sender_value = use_sender_value and sender_value and not channel_has_sender
if not (channel_has_sender or has_sender_column or has_sender_value):
    raise AttributeError("No value provided for the sender")

if not recipient_column:
    raise AttributeError("No value provided for the recipient")


# Validation part 2 - when necessary, check the column values provided are in the contacts (people) dataset
people_columns = [p['name'] for p in people.read_schema()]
for arg in ['subject', 'body']:
    if not globals()["use_" + arg + "_value"] and globals()[arg + "_column"] not in people_columns:
        raise AttributeError("The column you specified for %s (%s) was not found." % (arg, globals()[arg + "_column"]))

if not channel_has_sender and not use_sender_value and sender_column not in people_columns:
    raise AttributeError("The column you specified for sender (%s) was not found." % sender_column)

if recipient_column not in people_columns:
    raise AttributeError("The column you specified for recipient (%s) was not found." % recipient_column)


# Create Jinja templates if needed

body_template = None
if use_body_value:
    if body_format == 'html':
        body_template = jinja_env.from_string(html_body_value)
    else:
        body_template = jinja_env.from_string(body_value)

subject_template = None
if use_subject_value:
    subject_template = jinja_env.from_string(subject_value)

# Write schema
output_schema = list(people.read_schema())
output_schema.append({'name': 'sendmail_status', 'type': 'string'})
output_schema.append({'name': 'sendmail_error', 'type': 'string'})
output.write_schema(output_schema)

attachment_files = build_attachment_files(attachment_datasets, attachment_type)

attachments_templating_dict = attachments_template_dict(attachment_datasets)

if mail_channel is None or mail_channel == 'direct_smtp':
    email_client = SmtpEmailClient(not use_html_body_value, read_smtp_config(config))
else:
    email_client = ChannelClient(not use_html_body_value, to_real_channel_id(mail_channel))

with output.get_writer() as writer:
    i = 0
    success = 0
    fail = 0
    try:
        for contact in people.iter_rows():
            recipient = contact[recipient_column]
            if recipient:
                logging.info("Sending to %s" % contact[recipient_column])
            else:
                logging.info("No recipient for row - emailing will fail - row data: %s" % contact)
            contact_dict = dict(contact)
            try:
                send_email_for_contact(email_client, contact_dict, body_template, subject_template)
                contact_dict['sendmail_status'] = 'SUCCESS'
                success += 1
                if writer:
                    writer.write_row_dict(contact_dict)
            except Exception as e:
                logging.exception("Send failed")
                fail += 1
                contact_dict['sendmail_status'] = 'FAILED'
                contact_dict['sendmail_error'] = str(e)
                if writer:
                    writer.write_row_dict(contact_dict)
            i += 1
            if i % 5 == 0:
                logging.info("Sent %d mails (%d success %d fail)" % (i, success, fail))
    except RuntimeError as runtime_error:
        # https://stackoverflow.com/questions/51700960/runtimeerror-generator-raised-stopiteration-every-time-i-try-to-run-app
        logging.info("Exception {}".format(runtime_error))
email_client.quit()
