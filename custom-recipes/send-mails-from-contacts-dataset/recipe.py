import dataiku
from dataiku.customrecipe import get_output_names_for_role, get_input_names_for_role, get_recipe_config
import logging
from dku_email_client import SmtpConfig, SmtpEmailClient, ChannelClient
from dss_selector_choices import SENDER_SUFFIX
from dku_attachment_handling import build_attachment_files, attachments_template_dict
from email_utils import build_email_subject, build_email_message_text
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
    # Remove suffix added in dynamic_form when the channel has a sender
    if channel_id.endswith(SENDER_SUFFIX):
        return channel_id[:-len(SENDER_SUFFIX)]
    else:
        return channel_id

def does_channel_have_sender(channel_id):
    return channel_id is not None and channel_id.endswith(SENDER_SUFFIX)


# Get handles on datasets
output_A_names = get_output_names_for_role('output')
output = dataiku.Dataset(output_A_names[0]) if len(output_A_names) > 0 else None
project_key = output.project_key

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

# Also applies to HTML as of 12.6.2
apply_coloring_excel = config.get('apply_coloring_excel', False)

# For legacy configs, assume it is text if not defined
body_format = config.get('body_format', 'text')
# For sending a body from a column value we also assume it is plain text - that is the legacy behavour
use_html_body_value = use_body_value and (body_format == 'html')

html_body_value = config.get('html_body_value', None)
mail_channel = config.get('mail_channel', None)
channel_has_sender = does_channel_have_sender(mail_channel)

attachment_type = config.get('attachment_type', "csv")

# Validation part 1 - Check some kind of value/column exists for body, subject, sender and recipient

is_body_present = False
if use_body_value:
    if use_html_body_value:
        is_body_present = bool(html_body_value)
    else:
        is_body_present = bool(body_value)
else:
    is_body_present = bool(body_column)
if not is_body_present:
    raise AttributeError("No body column nor body value specified")

is_subject_present = False
if use_subject_value:
    is_subject_present = bool(subject_value)
else:
    is_subject_present = bool(subject_column)
if not is_subject_present:
    raise AttributeError("No value provided for the subject")

is_sender_present = False
if use_sender_value:
    is_sender_present = bool(sender_value)
else:
    is_sender_present = bool(sender_column)
if not (channel_has_sender or is_sender_present):
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

attachment_files = build_attachment_files(attachment_datasets, attachment_type, apply_coloring_excel)

attachments_templating_dict = attachments_template_dict(attachment_datasets, project_key, apply_coloring_excel)

if mail_channel is None or mail_channel == '__DKU__DIRECT_SMTP__':
    email_client = SmtpEmailClient(not use_html_body_value, read_smtp_config(config))
else:
    email_client = ChannelClient(not use_html_body_value, to_real_channel_id(mail_channel))
email_client.login()

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
                email_subject = build_email_subject(use_subject_value, subject_template, subject_column, contact_dict)
                email_body_text = build_email_message_text(use_body_value, body_template, attachments_templating_dict, contact_dict, body_column,
                                                         use_html_body_value)
                recipient = contact_dict[recipient_column]
                # Note - if the channel has a sender configured, the sender value will be ignored by the email client here
                sender = sender_value if use_sender_value else contact_dict.get(sender_column, "")
                email_client.send_email(sender, recipient, email_subject, email_body_text, attachment_files)

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
