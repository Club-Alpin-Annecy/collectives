"""In-process scheduler for periodic maintenance tasks."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from collectives.utils.loxya_sync import sync_all_users
from collectives.utils.misc import purge_expired_accounts

LOGGER = logging.getLogger(__name__)


def init_scheduler(app):
    """Start the background scheduler, unless disabled.

    Disabled under tests (``TESTING``) so the test suite, which recreates
    the app for every test, does not spawn a scheduler thread per test.

    :param app: The Flask application.
    :return: The started scheduler, or None if disabled.
    """
    if app.config.get("TESTING") or not app.config.get("SCHEDULER_ENABLED", True):
        return None

    scheduler = BackgroundScheduler(timezone="Europe/Paris")

    def _purge_expired_accounts_job():
        """Run :func:`purge_expired_accounts` within the app context."""
        with app.app_context():
            purge_expired_accounts()

    scheduler.add_job(
        _purge_expired_accounts_job,
        CronTrigger(day=1, hour=3, minute=0),
        id="purge_expired_accounts",
        replace_existing=True,
    )
    if app.config.get("LOXYA_SYNC_ENABLED", True):

        def _loxya_sync_job():
            """Run :func:`sync_all_users` within the app context."""
            with app.app_context():
                sync_all_users()

        # Nightly rather than event driven: a licence expiry is a date passing,
        # no request of ours runs at that moment.
        scheduler.add_job(
            _loxya_sync_job,
            CronTrigger(hour=4, minute=30),
            id="loxya_sync",
            replace_existing=True,
        )

    scheduler.start()
    app.extensions["scheduler"] = scheduler

    LOGGER.info(
        "Background scheduler started (%s)",
        ", ".join(job.id for job in scheduler.get_jobs()),
    )
    return scheduler
