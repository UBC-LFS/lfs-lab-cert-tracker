from django.shortcuts import redirect

def handle_redirect(func):
    def hr(request, *args, **kwargs):
        try:
            res = func(request, *args, **kwargs)
            if request.method == 'POST' and 'redirect_url' in request.POST:
                return redirect(request.POST['redirect_url'])
            return res
        except Exception as e:
            return redirect('/error/%s'%(e))
    return hr
