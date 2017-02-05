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
