# unbound-modules
This repository contains a collections of custom [python module scripts](https://www.unbound.net/documentation/pythonmod/index.html) for the [unbound](https://www.unbound.net/) dns resolver.

For the modules to be used, unbound must be compiled [with python module support enabled](https://www.unbound.net/documentation/pythonmod/install.html#compiling). Out of the box, unbound only supports one python module instance at the same time (see [unbound#1213](https://www.unbound.net/documentation/pythonmod/install.html#compiling)). The default python module implementation also has another issue ([unbound#1212](https://www.nlnetlabs.nl/bugs-script/show_bug.cgi?id=1212)), that affects some of the modules below. I'm maintaining a [fork "unbound-python+"](https://github.com/episource/unbound) with the necessary patches built-in.

For [Arch Linux](https://www.archlinux.org/), I'm also maintaining PKGBUILDs: ["unbound-python"](https://github.com/episource/archlinux-overlay/tree/master/unbound-python) for unbound compiled with python module support enabled and ["unbound-python+"](https://github.com/episource/archlinux-overlay/tree/master/unbound-python%2B) including my patches for the issues mentioned above.

## Prerequisites
* unbound compiled with python module support (`--with-pythonmodule`)
* optional: ["unbound-python+"](https://github.com/episource/unbound) with patches for [unbound#1212](https://www.nlnetlabs.nl/bugs-script/show_bug.cgi?id=1212), [unbound#1213](https://www.nlnetlabs.nl/bugs-script/show_bug.cgi?id=1213) and [unbound#1214](https://www.nlnetlabs.nl/bugs-script/show_bug.cgi?id=1214)

## Install
1. **Copy the module script** (e.g. `the_module.py`) to your machine. Choose a location that fits your needs, e.g. `/etc/unbound/modules/the_module.py`.
2. **Activate unbound's python module** - add to `/etc/unbound/unbound.conf`:
    
    ```
    server:
      module-config: "validator python iterator"
      chroot: ""
      
    python:
      python-script: "/etc/unbound/modules/the_module.py"
    ```
    * `chroot: ""` - disables chroot which is not supported by unbound's python module.
    * `module-config:` - Unbound uses a mesh of plugins to process queries. The order in which a query is processed is controlled by `module-config:`. A query is passed from left to right and a response from right to left. The default configuration is `module-config: "validator iterator"`. The position of the python module depends on the requirements of the module script being used. The usual position is inbetween `validator` and `iterator`.
    * `python-script:` - the path of the module script file to be used.
    
    Out of the box, unbound supports only one instance of the python module and hence only one module script. When using ["unbound-python+"](https://github.com/episource/unbound), multiple instances can be used: Just add the word `python` more than once to the `module-config:`-section. The first instance uses the module script referenced by the first `python-script:`-option. The second instances the script of the second option, and so on.
    
    ```
    server:
      module-config: "validator python python iterator"
      chroot: ""
      
    python:
      python-script: "/etc/unbound/modules/the_module1.py"
      python-script: "/etc/unbound/modules/the_module2.py"
    ```
    
3. **Configure module scripts**: most module scripts load their configuration from a python module named `pythonmod_conf`. The corresponding file `pythonmod_conf.py` is searched in unbound's config directory (`/etc/unbound`) and using python's default search path. See a module script's description for further details.

# nxforward (nxforward.py)
If a query cannot be resolved (NXDOMAIN, other error code, no response, ...) and it matches one of the configured forward rules, a cname record is created and resolved on the fly to forward the query to another domain.

**Example:** Consider the query `your-host.`: `your-host.` is resolved to NXDOMAIN, but assume there's a matching forward rule to `lan.your-domain.net.`. Hence the `nxforward`-module generates a cname record `your-host. 60 IN CNAME your-host.lan.your-domain.net.` and makes unbound resolve it, effectively redirecting the query to another domain. 

Basic functionality is available when using an unpatched unbound resolver. Advanced features are available when using "unbound-python+" (see above):
 * When using "unbound-python+", recursive redirects can be resolved. When using an unpatched unbound resolver, the response after applying the first matching forward rule is returned to the client (possibly NXDOMAIN or another error). Circular redirects should be avoided when using either of them.
 * If an upstream resolver returns no answer and the query is matching any of the forward rules, an unpatched unbound will return SERVFAIL - "unbound-python+" applies the forward rule as expected.

## Configuration
The module script imports the configuration file `pythonmod_conf.py`. An sample configuration could look like this:

```python
#nxforward_ttl = 60
nxforward_rules = [ 
    ('*.'                     ,'lan.your-domain.net.' ),
    ('**.lan.'                ,'lan.your-domain.net.' ),
    ('**.lan.your-domain.net.','dhcp.your-domain.net.')
]
```

* `nxforward_ttl` - the ttl (time to live) of auto-generated cname records. The default is `60`
* `nxforward_rules` - an ordered list of forward rules applied to queries that can't be resolved (NXDOMAIN, other error code, no response, ...). The first matching rule is used to forward the query. A query rule consists of query pattern and a target domain. The query pattern starts with a wildcard and ends with an explicit domain name. Possible wildcards are `*` to match a single label (a non-empty string without dot) and `**` to match one are many labels. If no wildcard is given, `*` is used as implicit default. The cname record to forward the query is generated by appending the wildcard part of the query string with the given target domain.