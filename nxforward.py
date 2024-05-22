import re
import pprint
from pythonmod_conf import *
from collections import OrderedDict

##
## python module definition
##

def init(id, cfg):
    global nxforward_rules, nxforward_ttl, _rules, _ttl

    try:
        conf = OrderedDict(nxforward_rules)
    except NameError:
        raise NameError("nxfoward_rules configuration variable not defined")

    try:
        _ttl = nxforward_ttl
    except NameError:
        log_info("nxforward_ttl configuration variable not defined - using default")
        _ttl = 60
    
    _rules = OrderedDict()
    for pattern,target in conf.items():
        p = pattern.strip(".")
        if pattern.startswith("*"):
            if pattern.startswith("*."):
                regex_pattern = r"^([^\.]+\.)" + p[2:] + r"\.?$"
            elif pattern.startswith("**."):
                regex_pattern = r"^([^\.]+\.)+" + p[3:] + r"\.?$"
            else:
                raise ValueError("illegal nxforward pattern: " + pattern)
        else:
            regex_pattern = r"^([^\.]+\.)" + p + r"\.?$"

        regex = re.compile(regex_pattern, flags=re.IGNORECASE)
        _rules[regex] = target.strip(".") + "."

    return True

def deinit(id):
    return True

def inform_super(id, qstate, superqstate, qdata):
    return True

def operate(id, event, qstate, qdata):
    global _rules, _ttl
   
    # workaround qdata being None in unpatched versions of unbound
    # => recursive forward rules will be broken
    # see also #1212
    if qdata is None:
        # important: qdata is lost inbetween invocations!
        qdata = { "persistance": False }
    else:
        qdata["persistance"] = True
    
    # query was passed from the previous module or new query
    # => pass on to the next module
    if event == MODULE_EVENT_NEW or event == MODULE_EVENT_PASS:
        qstate.ext_state[id] = MODULE_WAIT_MODULE
        return True
    
    # there's an response (from the next module)
    # => check if response is nxdomain, error or empty; if so: apply forward rules
    if event == MODULE_EVENT_MODDONE:
        # empty responses require persistance to be available to
        # distinguish whether the empty response belongs to the initial query
        # or the forwarded query
        # note: get_return_msg_rcode returns RCODE_SERVFAIL on empty response
        if not (qdata["persistance"] or qstate.return_msg):
            log_warn("qdata not persistant (see #1212) and no response objecte available - skipping query")
        else:
            if get_return_msg_rcode(qstate.return_msg) != RCODE_NOERROR \
                    or qstate.return_msg.rep.an_numrrsets == 0:
                qname = qdata.get("cname", qstate.qinfo.qname_str)
                cname = apply_forward_rules(qname)
                
                # important: the forward rule might resolve to NXDOMAIN
                #            (or some other result != NOERROR)
                # with persistent qdata, cname eventually evaluates to None
                # (assuming no circular forward rules)
                # => no endless loop, NXDOMAIN is returned to the client
                # without persistent qdata, cname is calculated by always 
                # applying the forward rules to the initial query
                # => check if response already contains the cname rr
                if cname and not has_cname_rr(qstate.return_msg, qname, cname):
                    qdata["cname"] = cname
                    
                    # prepare a cname response...
                    qi = qstate.qinfo
                    cname_msg = DNSMessage(qname, qi.qtype, qi.qclass, PKT_QR | PKT_RD | PKT_RA)
                    cname_msg.answer.append("%s %d IN CNAME %s" % (qname, _ttl, cname))
                    cname_msg.set_return_msg(qstate)

                    # ...put it into the cache...
                    is_referral = 1
                    invalidateQueryInCache(qstate, qstate.return_msg.qinfo)
                    storeQueryInCache(qstate, qstate.return_msg.qinfo, qstate.return_msg.rep, is_referral)

                    # ...and restart the iterator / the next module
                    # important: set no_cache_store=1 to prevent the iterator
                    #            overwriting cached entries when forwarding
                    #            recursively!
                    # MODULE_RESTART_NEXT from util/module.h:module_ext_state
                    MODULE_RESTART_NEXT = 3
                    qstate.no_cache_store = 1
                    qstate.ext_state[id] = MODULE_RESTART_NEXT
                    return True
        
        # a    utomated caching has been disabled while forwarding
        # and forwarding breaks dnssec validation
        # => cache explicitly + force security status
        # important: take care of unbound without qdata support
        if qstate.return_msg and ( qdata.get("cname", None) \
                or (not qdata["persistance"] and apply_forward_rules(qstate.qinfo.qname_str)) ):
            # disable dnssec validation for modified response
            qstate.return_msg.rep.security = sec_status_indeterminate
            
            # explicitly cache response
            is_referral = 0
            qstate.no_cache_store = 0
            invalidateQueryInCache(qstate, qstate.qinfo)
            storeQueryInCache(qstate, qstate.qinfo, qstate.return_msg.rep, is_referral)

            log_info("serving forward response")
        
        qstate.ext_state[id] = MODULE_FINISHED
        return True
    
    log_err("pythonmod: unexpected event")
    qstate.ext_state[id] = MODULE_ERROR
    return True


##
## utility functions
##

# Calculate approriate cname or None if no redirect rule matches.
def apply_forward_rules(qname):
    global _rules
    
    for regex,target in _rules.items():
        host_matcher = regex.match(qname)
        if not host_matcher:
            continue
            
        # note: host ends with a dot
        host = host_matcher.group(1)
        return host + target

    return None

# extract dns names from binary rr_data
def extract_dns_names_from_rr_data(rrdata):
    names = []
    for i in range(0, rrdata.count):
        enc_name = rrdata.rr_data[i]
        name = ""
        
        # first two bytes contain the payload length
        # third byte is the length of the first label
        lbl_remain = enc_name[2]
        #log_warn("decoding enc_name: " + pprint.pformat(enc_name))
        for c in enc_name[3:]:
            if lbl_remain == 0:
                name += "."
                lbl_remain = c
                continue
        
            lbl_remain -= 1
            name += chr(c) 
        
        names += [ name ]

    return names

# Extract the response status code (RCODE_NOERROR, RCODE_NXDOMAIN, ...).
def get_return_msg_rcode(return_msg):
    if not return_msg:
        return RCODE_SERVFAIL

    # see macro FLAGS_GET_RCODE in util\net_help.h
    return return_msg.rep.flags & 0xf

# Get whether the response already contains a cname frecord for
# `qname` redirecting to `cname`.
def has_cname_rr(response, qname, cname):
    if not response:
        return False

    r = response.rep
    for i in range (0, r.an_numrrsets):
        rr = r.rrsets[i]
        if rr.rk.dname_str == qname and cname in extract_dns_names_from_rr_data(rr.entry.data):
            return True
            
    return False

