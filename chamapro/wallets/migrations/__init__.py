from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('chamas', '0001_initial'),  # adjust to your latest migration
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('is_frozen', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('membership', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='wallet',
                    to='chamas.membership',
                )),
            ],
            options={'verbose_name': 'Member Wallet', 'verbose_name_plural': 'Member Wallets', 'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='GroupWallet',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('total_contributions_received', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('total_disbursed', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chama', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='group_wallet',
                    to='chamas.chama',
                )),
            ],
            options={'verbose_name': 'Group Wallet', 'verbose_name_plural': 'Group Wallets'},
        ),
        migrations.CreateModel(
            name='WalletTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tx_type', models.CharField(
                    choices=[
                        ('topup', 'M-Pesa Top-Up'),
                        ('contribution', 'Contribution'),
                        ('loan_repayment', 'Loan Repayment'),
                        ('withdrawal', 'Withdrawal to M-Pesa'),
                        ('transfer_in', 'Transfer In'),
                        ('transfer_out', 'Transfer Out'),
                        ('reversal', 'Reversal'),
                    ],
                    max_length=20,
                )),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('completed', 'Completed'),
                        ('failed', 'Failed'),
                        ('reversed', 'Reversed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('reference', models.CharField(blank=True, db_index=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('balance_after', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('wallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='transactions',
                    to='wallets.wallet',
                )),
                ('contribution', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='wallet_transactions',
                    to='chamas.contribution',
                )),
                ('loan', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='wallet_transactions',
                    to='chamas.loan',
                )),
                ('peer_wallet', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='paired_transaction',
                    to='wallets.wallettransaction',
                )),
            ],
            options={'verbose_name': 'Wallet Transaction', 'verbose_name_plural': 'Wallet Transactions', 'ordering': ['-created_at']},
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['wallet', 'status', 'tx_type'], name='wallet_tx_status_idx'),
        ),
        migrations.AddIndex(
            model_name='wallettransaction',
            index=models.Index(fields=['reference'], name='wallet_tx_ref_idx'),
        ),
        migrations.CreateModel(
            name='WithdrawalRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('phone_number', models.CharField(max_length=15)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending Approval'),
                        ('approved', 'Approved'),
                        ('rejected', 'Rejected'),
                        ('paid', 'Paid Out'),
                        ('failed', 'Payout Failed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('rejection_reason', models.TextField(blank=True)),
                ('mpesa_reference', models.CharField(blank=True, max_length=100)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('wallet', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='withdrawal_requests',
                    to='wallets.wallet',
                )),
                ('approved_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='approved_withdrawals',
                    to='auth.user',
                )),
            ],
            options={'verbose_name': 'Withdrawal Request', 'verbose_name_plural': 'Withdrawal Requests', 'ordering': ['-created_at']},
        ),
    ]