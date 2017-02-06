##
## This is a sample configuration for the module scripts found in the
## repository https://github.com/episource/unbound-modules
##

##
## nxforward configuration section

# TTL (time to lieve) of auto-generated cname records in seconds.
# Default is 60s.
#nxforward_ttl = 60

# The ordered list of nxforward rules applied to queries that can't be resolved
# (NXDOMAIN, other error code, no response, ...). The first matching rule is 
# used to forward the query. A query rule consists of query pattern and a target
# domain. The query pattern starts with a wildcard and ends with an explicit
# domain name. Possible wildcards are `*` to match a single label (a non-empty
# string without dot) and `**` to match one are many labels. If no wildcard is
# given, `*` is used as implicit default. The cname record to forward the query
# is generated by appending the wildcard part of the query string with the given
# target domain.
# No default available. The nxforward module refuses to load without.
nxforward_rules = [ 
    ('*.'                     ,'lan.your-domain.net.' ),
    ('**.lan.'                ,'lan.your-domain.net.' ),
    ('**.lan.your-domain.net.','dhcp.your-domain.net.')
]
