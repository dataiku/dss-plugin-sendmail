import dataiku
from dataiku.customrecipe import get_output_names_for_role, get_input_names_for_role, get_recipe_config
import logging
from email_client import SmtpConfig, SmtpEmailClient
from attachment_handling import build_attachments, attachments_template_dict
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


def send_email_for_contact(mail_client, contacts_row, message_template):
    """
    Send an email with the relevant data for the contacts_row and given template
    :param mail_client: SmtpEmailClient
    :param contacts_row: dict
    :param message_template: jinja Template|None - email template or None if this is to be generated from the row data
    Sends the message or throws an exception
    """

    logging.info(attachments_templating_dict)

    recipient = contacts_row[recipient_column]
    if use_body_value:
        if message_template:
            templating_value_dict = dict(contacts_row)
            templating_value_dict["attachments"] = attachments_templating_dict
            try:
                email_text = message_template.render(templating_value_dict)
            except Exception as exp:
                raise Exception("Could not render template: {} ".format(exp))
        else:
            raise Exception("No template was generated to use for the message")
    else:
        email_text = contacts_row.get(body_column, "")

    email_subject = subject_value if use_subject_value else contacts_row.get(subject_column, "")
    sender = sender_value if use_sender_value else contacts_row.get(sender_column, "")
    mail_client.send_email(sender, recipient, email_text, email_subject, mime_parts, body_encoding)


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Get handles on datasets
output_A_names = get_output_names_for_role('output')
output = dataiku.Dataset(output_A_names[0]) if len(output_A_names) > 0 else None

people = dataiku.Dataset(get_input_names_for_role('contacts')[0])
attachments = [dataiku.Dataset(x) for x in get_input_names_for_role('attachments')]

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
use_html_body_value = config.get('use_html_body_value', False)

body_column = config.get('body_column', None)
body_value = config.get('body_value', None)
html_body_value = config.get('html_body_value', None)

body_encoding = config.get('body_encoding', 'us-ascii')

smtp_config = read_smtp_config(config)

attachment_type = config.get('attachment_type', "csv")

# Some validation, check we have things we really need
if not body_column and not (use_body_value and body_value) and not (use_html_body_value and html_body_value):
    raise AttributeError("No body column nor body value specified")

people_columns = [p['name'] for p in people.read_schema()]
for arg in ['sender', 'subject', 'body']:
    if not globals()["use_" + arg + "_value"] and globals()[arg + "_column"] not in people_columns:
        raise AttributeError("The column you specified for %s (%s) was not found." % (arg, globals()[arg + "_column"]))

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

mime_parts = build_attachments(attachments, attachment_type)
attachments_templating_dict = attachments_template_dict(attachments)

email_client = SmtpEmailClient(smtp_config, use_html_body_value)

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
