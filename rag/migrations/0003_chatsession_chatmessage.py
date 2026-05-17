import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('rag', '0002_documentchunk'),
	]

	operations = [
		migrations.CreateModel(
			name='ChatSession',
			fields=[
				('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
				('title', models.CharField(blank=True, max_length=255)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('updated_at', models.DateTimeField(auto_now=True)),
			],
			options={
				'ordering': ['-updated_at'],
			},
		),
		migrations.CreateModel(
			name='ChatMessage',
			fields=[
				('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
				('role', models.CharField(choices=[('user', 'User'), ('assistant', 'Assistant')], max_length=20)),
				('content', models.TextField()),
				('sources', models.JSONField(blank=True, default=list)),
				('created_at', models.DateTimeField(auto_now_add=True)),
				('session', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='messages', to='rag.chatsession')),
			],
			options={
				'ordering': ['created_at', 'id'],
			},
		),
	]