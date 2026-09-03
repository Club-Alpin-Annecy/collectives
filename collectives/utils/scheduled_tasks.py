"""In-process scheduler for periodic maintenance tasks."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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
    scheduler.start()
    app.extensions["scheduler"] = scheduler

    LOGGER.info("Background scheduler started (purge_expired_accounts: monthly)")
    return scheduler
