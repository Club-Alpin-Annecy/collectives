Application configuration
=======================================

Configuration is achieved bu two means:

* `Cold configuration`_, using local file.
* `Hot configuration`_, in HMI 


Cold configuration
--------------------

It contains basic and highly technical data. It is meant to be tweaked 
by a technician and requires a full reboot to be taken into account.

Default configuration is in `config.py`. Override paramteters should be in `instance/config.py`.

Most configuration variables can be set using eponym environment variables.

Cold configuration description
.................................

.. automodule:: config
    :members:

Hot configuration
--------------------

This configuration contains less technical data, such as login credentials
to external third parties (extranet, SMTP), appereance, and naming. It is
saved in database.

Default configuration is stored in `collectives/configuration.yaml`.

Configuration is modified on '/technician/configuration' by a technician or 
an administrator.

Hot configuration types
..........................

See :py:class:`collectives.models.configuration.ConfigurationTypeEnum`

