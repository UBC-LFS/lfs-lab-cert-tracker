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

REQUEST_STATUS = [ (k, v) for k, v in REQUEST_STATUS_DICT.items() ]

