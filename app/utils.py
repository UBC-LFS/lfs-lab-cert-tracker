NUM_PER_PAGE = 20

class UserRole:
    USER = 0
    PRINCIPAL_INVESTIGATOR = 1
    PI_PROXY = 2

    CHOICES = [
        (PRINCIPAL_INVESTIGATOR, "Supervisor"),
        (PI_PROXY, "Supervisor Proxy"),
        (USER, "User"),
    ]

    @staticmethod
    def get_role_text(role):

        return dict(UserRole.CHOICES).get(int(role))
