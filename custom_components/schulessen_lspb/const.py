"""Constants for the Schulessen (OPC WebApp) integration."""

DOMAIN = "schulessen_lspb"

CONF_KARTENNUMMER = "kartennummer"
CONF_BASE_URL = "base_url"
CONF_MANDANT = "mandant"

DEFAULT_BASE_URL = "https://schulessen-bestellung.lspb.de"
DEFAULT_SCAN_INTERVAL_MINUTES = 240

# From this hour onwards, the "current meal" sensor switches from today's
# order to the next school day's - ordering closes at 15:00 the day before,
# so shortly before that is when "today" stops being the interesting answer.
CONF_SWITCH_HOUR = "switch_hour"
DEFAULT_SWITCH_HOUR = 14

ATTR_DATE = "date"
ATTR_WEEKDAY = "weekday"
ATTR_OPTIONS = "options"
ATTR_ORDERED = "ordered"
ATTR_PRICE = "price"
ATTR_COLUMN = "column"
ATTR_DESCRIPTION = "description"
