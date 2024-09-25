# magento-carding-defense
Prevent carding attacks in Magento 2

This repository is designed to help people implement layers of defense against carding attacks in Magento 2.
Carding attacks are where someone quickly tries thousands of stolen credit cards, to determine which ones
can successfully place orders so they know which ones have not yet been reported stolen and can be used
on other website. They probably don't care about your site at all but are just using it to check if it
allows them to place an order.

You'll need to modify the files provided to suit your server and your needs.

The first defense is in modsecurity/crs/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf. Once you have
modsecurity and the CRS installed, you can copy what is in here to your
modsecurity/crs/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf file. You may need to modify the rule IDs
and the thresholds.

This modsecurity rule is designed to reject any payment attempts if more than 10 are received from an IP
address in the past 2 hours. The idea is that 10 payment attempts should be more than enough for any
legitimate customer, and the 2 hour window helps in blocking carding attacks where they are using so
many IP addresses that each individual IP isn't making requests very quickly. It will also block
attacks where they are accessing the site very quickly from one IP address.


The second defense is in the fail2ban directory. These rules are designed for if you are using Magento
with nginx. Again, modify them to suit your needs. By default they will block an IP address from the
entire site for 10 minutes if modsecurity has blocked 3 requests from them in the past 10 minutes. This
rule is generic so it will apply for the carding attack modsecurity rule, as well as other modsecurity
rules. The goal is that if someone is attacking the site, you'd rather block them with the firewall
rather than let them keep trying to access the site.


The third defense is the auto_payment_captcha python script. The reason for this is that the modsecurity
rule doesn't always help if there is a large-scale attack coming from hundreds or thousands of
individual IP addresses. The attacker may have each IP address try only 5 different credit cards so
modsecurity may not block them. This script will monitor Magento's payment.log file to watch for
payment failures and if there are more than 30 failures in an hour (by default) it will enable a
captcha on Braintree's credit card form. Then, after an hour it will disable the captcha.

I'd rather not leave the captcha on at all times because of the friction it causes for ordinary
customers, but for attackers that friction is very useful. So, even if a carding attack comes from
thousands of unique IP addresses, this will temporarily stop them after they've only tried 30 credit
cards.

You'll want to modify that threshold depending on your site's traffic. A good starting point for the
threshold would be to at least double the number of payment failures that your site would normally
get in an hour.

You'll also need to modify it if you don't use Braintree as your credit card processor. You'll need to
check to see what line is outputted in payment.log for a failure, and also modify the line that enables
the captcha in Magento's configuration.

The other file in that directory can be used to make systemd automatically start the script.
