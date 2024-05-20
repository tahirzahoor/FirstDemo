
import datetime
from django.apps import AppConfig


class MyappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myapp'
    # my_scheduled_task.schedule(repeat=Task.DAILY, time=datetime.time(hour=8, minute=0))
    # print("MyappConfig", "MyappConfig")
