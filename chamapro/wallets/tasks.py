# wallets/tasks.py
"""
Celery beat task for auto-deducting contributions on due dates.

Add to settings.py:
    CELERY_BEAT_SCHEDULE = {
        'auto-deduct-contributions': {
            'task': 'wallets.tasks.auto_deduct_contributions',
            'schedule': crontab(hour=7, minute=0),  # runs daily at 7 AM EAT
        },
    }

Also requires:
    pip install celery redis django-celery-beat
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
"""
import logging
from celery import shared_task
from .services import AutoDeductService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def auto_deduct_contributions(self):
    """
    Daily task: deduct due contributions from member wallets
    and credit the chama group wallet.
    """
    try:
        summary = AutoDeductService.run_all_chamas()
        total_success = sum(len(v['success']) for v in summary.values())
        total_skipped = sum(len(v['skipped']) for v in summary.values())
        total_errors  = sum(len(v['errors'])  for v in summary.values())
        logger.info(
            "AUTO_DEDUCT_TASK complete: success=%s skipped=%s errors=%s",
            total_success, total_skipped, total_errors,
        )
        return summary
    except Exception as exc:
        logger.exception("AUTO_DEDUCT_TASK failed: %s", exc)
        raise self.retry(exc=exc)