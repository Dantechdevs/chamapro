# wallets/management/commands/run_auto_deduct.py
"""
Manual trigger (no Celery needed):
    python manage.py run_auto_deduct
    python manage.py run_auto_deduct --chama-id 3
"""
import json
from django.core.management.base import BaseCommand
from wallets.services import AutoDeductService


class Command(BaseCommand):
    help = 'Run auto-deduction of contributions from member wallets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--chama-id',
            type=int,
            default=None,
            help='Run for a specific chama only (omit to run all)',
        )

    def handle(self, *args, **options):
        chama_id = options['chama_id']

        if chama_id:
            from chamas.models import Chama
            try:
                chama = Chama.objects.get(pk=chama_id)
            except Chama.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Chama #{chama_id} not found."))
                return

            self.stdout.write(f"Running auto-deduct for: {chama.name}...")
            result = AutoDeductService.run_for_chama(chama)
            summary = {chama.name: result}
        else:
            self.stdout.write("Running auto-deduct for ALL active chamas...")
            summary = AutoDeductService.run_all_chamas()

        for chama_name, result in summary.items():
            self.stdout.write(f"\n── {chama_name} ──")
            self.stdout.write(self.style.SUCCESS(f"  ✓ Success:  {len(result['success'])}"))
            self.stdout.write(self.style.WARNING(f"  ⚠ Skipped:  {len(result['skipped'])}"))
            if result['errors']:
                self.stdout.write(self.style.ERROR(f"  ✗ Errors:   {len(result['errors'])}"))

            for s in result['success']:
                self.stdout.write(f"    + {s['member']} KES {s['amount']} ref:{s['ref']}")
            for s in result['skipped']:
                self.stdout.write(f"    ~ {s['member']} — {s['reason']}")
            for e in result['errors']:
                self.stdout.write(self.style.ERROR(f"    ! {e['member']} — {e['error']}"))

        self.stdout.write("\nDone.")