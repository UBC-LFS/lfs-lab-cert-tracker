from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    name = 'scheduler'

    def ready(self):
        pass
        #from scheduler import tasks
        #tasks.run()
