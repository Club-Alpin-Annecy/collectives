Notification digests
====================

This branch introduces digest-based notifications for newly created collectives.

Implemented features
--------------------

The following behavior is implemented:

- users subscribed to new collective notifications receive a grouped digest instead of one email per created collective;
- digest frequency can be configured per user as daily or weekly;
- user license validity is checked again when the digest is sent;
- emails remind users to keep notifications limited and disable them when no longer needed;
- each notification email includes a one-click unsubscribe link;
- if a user does not click any notification link for one year, notifications are stopped after a warning period.

How scheduled execution works
-----------------------------

The application exposes two Flask CLI commands:

- ``flask --app collectives:create_app send-new-event-digests``
- ``flask --app collectives:create_app maintain-new-event-notifications``

They are intentionally kept outside the web server process. With the current
stack, the recommended execution model is an external scheduler such as
``cron`` or a ``systemd`` timer.

Cron example file
-----------------

An example cron file is provided here:

``doc/cron/collectives-notifications.cron``

Its purpose is:

- to send pending daily/weekly digests every morning;
- to apply the inactivity policy every morning.

Example content
...............

.. literalinclude:: ../cron/collectives-notifications.cron
   :language: crontab

How to use the cron file
------------------------

1. Copy the file to the target server.
2. Update the project path and virtualenv path in each command.
3. Install it on the single host responsible for background jobs.
4. Reload the user crontab.

Typical installation example:

.. code-block:: bash

   crontab doc/cron/collectives-notifications.cron

Or after editing a local copy:

.. code-block:: bash

   crontab /path/to/collectives-notifications.cron

Operational notes
-----------------

- run these jobs on only one application instance to avoid duplicate digests;
- the commands are safe to execute independently of the web server;
- keep SMTP configuration valid before enabling the jobs in production.
