import psycopg2
import copy
from datetime import datetime
#USER = os.environ['LFS_LAB_CERT_TRACKER_DB_USER']
#PASSWORD = os.environ['LFS_LAB_CERT_TRACKER_DB_PASSWORD']
#HOST = os.environ['LFS_LAB_CERT_TRACKER_DB_HOST']
#PORT = os.environ['LFS_LAB_CERT_TRACKER_DB_PORT']
#DATABASE = os.environ['LFS_LAB_CERT_TRACKER_DB_NAME']


class CertTrackerDatabase:

    def __init__(self, user, password, host, port, database):
        try:
            self.connection = psycopg2.connect(user=user, password=password, host=host, port=port, database=database)
            self.cursor = self.connection.cursor()

        except (Exception, psycopg2.Error) as error :
            print ("Error while connecting to PostgreSQL", error)

        finally:
            if self.connection:
                # Fetch data
                users, certs = self.fetch_data()
                self.users = users
                self.certs = certs

    def close(self):
        self.cursor.close()
        self.connection.close()

    def get_all_users(self):
        """ Get all users """

        self.cursor.execute("SELECT * FROM auth_user;")
        rows = self.cursor.fetchall()
        users = dict()
        for row in rows:
            is_active = row[9]
            if is_active:
                id = row[0]
                is_superuser = row[3]
                username = row[4]
                first_name = row[5]
                last_name = row[6]
                email = row[7]
                user = {
                    'id': id,
                    'is_superuser': is_superuser,
                    'username': username,
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'is_active': is_active,
                    'has_expiry_cert': False,
                    'labs': []
                }
                users[id] = user

        return users


    def get_all_labs(self):
        """ Get all labs """

        self.cursor.execute("SELECT * FROM lfs_lab_cert_tracker_lab;")
        rows = self.cursor.fetchall()
        labs = dict()
        for row in rows:
            id = row[0]
            name = row[1]
            lab = { 'id': id, 'name': name, 'pis': set(), 'certs': [] }
            labs[id] = lab

        return labs


    def get_all_certs(self):
        """ Get all certs """

        self.cursor.execute("SELECT * FROM lfs_lab_cert_tracker_cert;")
        rows = self.cursor.fetchall()
        certs = dict()
        for row in rows:
            id = row[0]
            name = row[1]
            cert = { 'id': id, 'name': name }
            certs[id] = cert

        return certs


    def get_all_userlabs(self):
        """ Get all userlabs """

        self.cursor.execute("SELECT * FROM lfs_lab_cert_tracker_userlab;")
        rows = self.cursor.fetchall()
        return [ { 'id': row[0], 'role': row[1],'lab_id': row[2], 'user_id': row[3] } for row in rows ]


    def get_all_labcerts(self):
        """ Get all labcerts """
        self.cursor.execute("SELECT * FROM lfs_lab_cert_tracker_labcert;")
        rows = self.cursor.fetchall()
        return [ { 'id': row[0], 'cert_id': row[1], 'lab_id': row[2] } for row in rows ]


    def get_all_usercerts(self):
        """ Get all usercerts """

        self.cursor.execute("SELECT * FROM lfs_lab_cert_tracker_usercert;")
        rows = self.cursor.fetchall()
        return [ {
            'id': row[0],
            'expiry_date': row[1],
            'cert_id': row[2],
            'user_id': row[3],
            'completion_date': row[6]
        } for row in rows ]


    def fetch_data(self):
        """ Fetch data, and users have labs' information and
        certificates' information """

        users = self.get_all_users()
        labs = self.get_all_labs()
        certs = self.get_all_certs()
        labcerts = self.get_all_labcerts()
        userlabs = self.get_all_userlabs()
        usercerts = self.get_all_usercerts()
        all_certs = copy.deepcopy(certs)
        
        # Add cert info to each lab
        for labcert in labcerts:
            lab = labs[ labcert['lab_id'] ]
            cert = certs[ labcert['cert_id'] ]
            lab['certs'].append(cert)

        # Add lab info to each user
        for userlab in userlabs:
            role = userlab['role']
            lab = labs[ userlab['lab_id'] ]
            user = users[ userlab['user_id'] ]

            if role == 1:
                lab['pis'].add(userlab['user_id'])

            user['labs'].append(lab)

        # Add cert info to each user's lab
        for usercert in usercerts:
            cert_id = usercert['cert_id']
            user_id = usercert['user_id']
            expiry_date = usercert['expiry_date']
            completion_date = usercert['completion_date']

            # Important!
            # Each lab should be updated by user_id for certificates
            labs = copy.deepcopy(users[user_id]['labs'])

            for lab in labs:
                certs = lab['certs']
                for cert in certs:
                    if cert_id == cert['id']:
                        cert['expiry_date'] = expiry_date
                        cert['completion_date'] = completion_date
                        if users[user_id]['has_expiry_cert'] == False:
                            users[user_id]['has_expiry_cert'] = expiry_date != completion_date

            users[user_id]['labs'] = labs

        return users, all_certs

    def get_users(self):
        """ get all users """

        return self.users

    def get_certs(self):
        """ get all certs """

        return self.certs

    def get_admin(self):
        """ Find administrators """

        admin = set()
        for id, user in self.users.items():
            if user['is_superuser'] == True:
                admin.add(user['id'])

        return admin
