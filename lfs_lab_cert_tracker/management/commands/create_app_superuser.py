from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError

"""
from lfs_lab_cert_tracker.models import User


class Command(createsuperuser.Command):
    help = 'Crate a superuser with a password'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--password', dest='password', default=None,
            help='Password for the superuser',
        )
        parser.add_argument(
            '--first_name', dest='first_name', default=None,
            help='First name',
        )
        parser.add_argument(
            '--last_name', dest='last_name', default=None,
            help='Last name',
        )
        parser.add_argument(
            '--cwl', dest='cwl', default=None,
            help='CWL of superuser',
        )

    def handle(self, *args, **options):
        password = options.get('password')
        username = options.get('username')
        database = options.get('database')

        first_name = options.get('first_name')
        last_name = options.get('last_name')
        email = options.get('email')
        cwl = options.get('cwl')

        if not all([password, username, database, first_name, last_name, email, cwl]):
            raise CommandError("One or more --username, --password, --database, --first_name, --last_name, --email, --cwl missing")

        # Call the original createsuperuser command
        super(Command, self).handle(*args, **options)

        if password:
            auth_user = self.UserModel._default_manager.db_manager(database).get(username=username)
            auth_user.set_password(password)
            auth_user.save()

        user = User.objects.create(
            id=auth_user.id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            cwl=username
        )
"""
