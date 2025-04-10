from django.utils.safestring import mark_safe

AFFLIATIONS = [ 
    ('0', 'I have a UBC employee ID'),
    ('1', 'I am an undergraduate student with a UBC student number'),
    ('2', 'I am a graduate student with a UBC student number'),
    ('3', mark_safe('I do not have a UBC Card. Apply at <a href="https://ubccard.ubc.ca" target="_blank">ubccard.ubc.ca</a>. Access cannot be granted without one.'))
]

AFTER_HOUR_ACCESS = [
    ('0', 'Yes, I will need after hours access'),
    ('1', 'No, I will not need after hours access')
]

APPROVED = '0'
DECLINED = '1'
INSUFFICIENT = '2'

REQUEST_STATUS_DICT = {
    APPROVED: 'Approved',
    DECLINED: 'Declined',
    INSUFFICIENT: 'Insufficient Info'
}

REV_REQUEST_STATUS_DICT = {
    'Approved': APPROVED,
    'Declined': DECLINED,
    'Insufficient Info': INSUFFICIENT
}

REQUEST_STATUS = [ (k, v) for k, v in REQUEST_STATUS_DICT.items() ]


URL_NEXT = {'basic_info': 'pis', 'pis': 'areas', 'areas':'trainings', 'trainings': 'basic_info'}

CREATE_ROOM_KEY = 'create_room_data'
EDIT_ROOM_KEY = 'edit_room_data'


EMAIL_FOOTER = '''\
<br />
<div>
    <b>Please note that if you try to access the LFS Training Record Management System off campus,
    you must be connected via
    <a href="https://it.ubc.ca/services/email-voice-internet/myvpn">UBC VPN</a>.</b>
</div>
<br />
<p>Best regards,</p>
<p>LFS Training Record Management System</p>
'''