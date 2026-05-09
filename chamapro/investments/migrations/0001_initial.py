from django.db import migrations, models
import django.conf
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('chamapro', '0001_initial'),  # ← update this to your actual last chamapro migration
    ]

    operations = [
        migrations.CreateModel(
            name='Investment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('investment_type', models.CharField(choices=[('mmf','Money Market Fund'),('fd','Fixed Deposit'),('real_estate','Real Estate / Land'),('stocks','NSE Stocks'),('business','Chama Business'),('other','Other')], max_length=20)),
                ('institution', models.CharField(blank=True, max_length=200)),
                ('capital_invested', models.DecimalField(decimal_places=2, max_digits=14)),
                ('date_invested', models.DateField()),
                ('maturity_date', models.DateField(blank=True, null=True)),
                ('current_value', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('status', models.CharField(choices=[('active','Active'),('matured','Matured'),('sold','Sold'),('exited','Exited')], default='active', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('chama', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investments', to='chamapro.chama')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='investments_created', to=django.conf.settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date_invested']},
        ),
        migrations.CreateModel(
            name='InvestmentUnit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('units_held', models.DecimalField(decimal_places=6, default=0, max_digits=18)),
                ('nav_at_entry', models.DecimalField(decimal_places=6, default=1, max_digits=14)),
                ('invested_amount', models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ('issued_at', models.DateTimeField(auto_now_add=True)),
                ('investment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='units', to='investments.investment')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='investment_units', to='chamapro.membership')),
            ],
            options={'unique_together': {('investment', 'member')}},
        ),
        migrations.CreateModel(
            name='InvestmentReturn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('return_type', models.CharField(choices=[('dividend','Dividend'),('interest','Interest'),('rental','Rental Income'),('capital_gain','Capital Gain'),('maturity','Maturity Payout')], max_length=20)),
                ('gross_amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('date_received', models.DateField()),
                ('flow', models.CharField(choices=[('reinvest','Reinvest into Portfolio'),('distribute','Distribute to Members')], max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('processed', models.BooleanField(default=False)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('investment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='returns', to='investments.investment')),
                ('recorded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=django.conf.settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-date_received']},
        ),
        migrations.CreateModel(
            name='ReturnDistribution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('units_at_time', models.DecimalField(decimal_places=6, max_digits=18)),
                ('share_percent', models.DecimalField(decimal_places=4, max_digits=8)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=14)),
                ('credited_to_wallet', models.BooleanField(default=False)),
                ('credited_at', models.DateTimeField(blank=True, null=True)),
                ('investment_return', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distributions', to='investments.investmentreturn')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='return_distributions', to='chamapro.membership')),
            ],
        ),
        migrations.CreateModel(
            name='NAVHistory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('nav_per_unit', models.DecimalField(decimal_places=6, max_digits=14)),
                ('total_value', models.DecimalField(decimal_places=2, max_digits=14)),
                ('total_units', models.DecimalField(decimal_places=6, max_digits=18)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('investment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nav_history', to='investments.investment')),
            ],
            options={'ordering': ['date'], 'unique_together': {('investment', 'date')}},
        ),
    ]