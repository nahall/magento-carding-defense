#!/usr/bin/env python3

# This script is designed to watch Magento's payment.log file for a line that
# Braintree outputs when there is a payment transaction that has
# failed. Once a certain threshold of failures in the given time period is
# met it will run a command to modify Magento's configuration to enable
# recaptcha_v3 for Braintree's credit card form, with the goal to block a
# large scale carder attack.
# Then after a certain amount of time has past it will disable the captcha
# so as to not annoy normal customers while there isn't a carder attack.

# You'll need to modify the variables to point to the correct log, to send
# notification to the correct email address, and set the thresholds to
# what you want. The failure threshold should probably be at least double
# what you would expect your site to get in normal operation, so it is
# high enough that it would be very rare to occur unless under a carding
# attack.

# If you are not using Braintree then you will also need to modify the
# log failure detection line and the Magento config parameters that
# start/stop the captcha.

import time
import subprocess
import smtplib
from email.message import EmailMessage
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta
import threading
from typing import Iterator

LOG_FILE = '/home/myuser/www/var/log/payment.log'
MAGENTO_BIN = '/home/myuser/www/bin/magento'
EMAIL_ADDRESS = 'me@mysite.com'
SMTP_SERVER = 'localhost'
PAYMENT_FAILURE_THRESHOLD = 30
PAYMENT_FAILURE_LOOKBACK_SECS = 3600
PAYMENT_CAPTCHA_SECS = 3600

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = EMAIL_ADDRESS
    with smtplib.SMTP(SMTP_SERVER) as s:
        s.send_message(msg)

def run_magento_command(command, *args):
    full_command = [MAGENTO_BIN] + command.split() + list(args)
    subprocess.run(full_command, check=True)

# This is designed to emulate the "tail -F" command, where it will
# watch the end of the file for new lines and also handle log
# rotation
def follow(file, sleep_sec=1) -> Iterator[str]:
    """ Yield each line from a file as they are written.
    `sleep_sec` is the time to sleep after empty reads. """
    file.seek(0, 2)  # Go to the end of the file
    while True:
        line = file.readline()
        if not line:
            time.sleep(sleep_sec)
            continue
        yield line


class LogHandler:
    def __init__(self):
        self.failure_times = deque(maxlen=PAYMENT_FAILURE_THRESHOLD)
        self.ignore_until = None

    def handle_line(self, line):
        now = datetime.now()
        
        if self.ignore_until and now < self.ignore_until:
            return

        # Modify this line to match what your payment processor outputs when there is a payment failure:
        if "'success' => false" in line:
            print(now)
            print(line, end='')
            print('--- PAYMENT FAILURE DETECTED')
            self.failure_times.append(now)

            if len(self.failure_times) == PAYMENT_FAILURE_THRESHOLD and (now - self.failure_times[0]) <= timedelta(seconds=PAYMENT_FAILURE_LOOKBACK_SECS):
                print('--- PAYMENT FAILURE PASSED THRESHOLD SO ENABLING CAPTCHA')
                send_email(
                    "Recaptcha Enabled",
                    "Too many payment failures so enabling recaptcha temporarily."
                )
                # Modify this line if you aren't using Braintree and need a different command to enable the captcha:
                run_magento_command('config:set', 'recaptcha_frontend/type_for/braintree', 'recaptcha_v3')
                self.ignore_until = now + timedelta(seconds=PAYMENT_CAPTCHA_SECS)
                self.failure_times.clear()
                self.schedule_disable_recaptcha()

    def schedule_disable_recaptcha(self):
        def disable():
            print(datetime.now())
            print('--- CLEARING CAPTCHA')
            # Modify this line if you aren't using Braintree and need a different command to disable the captcha:
            run_magento_command('config:set', 'recaptcha_frontend/type_for/braintree', '')
            self.ignore_until = None
        
        # Schedule the disable_recaptcha function to run after PAYMENT_CAPTCHA_SECS
        threading.Timer(PAYMENT_CAPTCHA_SECS, disable).start()

def monitor_log():
    handler = LogHandler()
    while True:
        try:
            with open(LOG_FILE, 'r') as file:
                for line in follow(file):
                    handler.handle_line(line)
        except FileNotFoundError:
            print(f"Log file {LOG_FILE} not found. Waiting for it to appear...")
            time.sleep(10)
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_log()
