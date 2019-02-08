import logging

from django.shortcuts import redirect
from django.db.utils import IntegrityError

logger = logging.getLogger(__name__)

def handle_redirect(func):
    def hr(request, *args, **kwargs):
        try:
            res = func(request, *args, **kwargs)
            if request.method == 'POST' and 'redirect_url' in request.POST:
                return redirect(request.POST['redirect_url'])
            return res
        except IntegrityError as ie:
            logger.error("IntegrityError: " + str(ie))
            return redirect('/error/%s'%("Invalid! Check if action already done"))
        except Exception as e:
            logger.error("Exception: " + str(e))
            return redirect('/error/%s'%(e))
    return hr
