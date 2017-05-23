from django.shortcuts import render
from BunqAPI.forms import GenerateKeyForm, decrypt_form
from BunqAPI.installation import installation
from BunqAPI.callbacks import callback
from django.utils.encoding import smart_str
from django.http import HttpResponse
# from django.contrib.auth import authenticate
from django.contrib.auth.models import User
# from django.contrib.auth.decorators import login_required
from django_otp.decorators import otp_required
import json
from django.contrib.sessions.models import Session
import os
# from pprint import pprint

# from django.http.response import FileResponse

# Create your views here.


@otp_required  # NOTE: forces the user to log in with 2FA
def generate(request):
    '''
    This is working smooth.
    View that handles the /generate page.

    Need to find a way to test views where OTP is required.
    Maybe with mock tests or monkeyPatch.
    '''
    if request.method == 'POST':
        formKey = GenerateKeyForm(request.POST)
        if formKey.is_valid():
            username = request.user.username
            API = formKey.cleaned_data['API']
            encryption_password = formKey.cleaned_data['encryption_password']
            data = installation(username, encryption_password, API)
            encryptedData = data.encrypt()

            registration = callback(
                json.loads(encryptedData),
                User.objects.get(username=request.user),
                encryption_password,
            ).register()

            if registration.status_code is 200:
                response = HttpResponse(
                    encryptedData, content_type='application/force-download')
                response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('BunqWebApp.json')  # noqa
            else:
                error = {
                    "Error": [{
                        "error_description_translated": 'something whent wrong while registering your API key wiht the bunq servers'  # noqa
                    }]
                }
                response = HttpResponse(json.dumps(error))
            return response

    else:
        formKey = GenerateKeyForm()
    return render(request, 'BunqAPI/index.html', {'form': formKey})


@otp_required
def decrypt(request):
    '''
    Need to rewrtie this to just show a page and load the form. # Done
    Need to use mock test or monkeyPatch.
    This view can be renamed.
    '''
    if request.method == 'POST':
        form = decrypt_form(request.POST)
    else:
        form = decrypt_form()
    return render(request, 'BunqAPI/decrypt.html', {'form': form})


@otp_required
def API(request, selector, userID=None, accountID=None):
    '''
    Need to mock bunq api response to test this view.
    The view that handles API calls.
    accountID === cardID
    '''
    if request.method == 'POST':
        f = json.loads(request.POST['json'])
        p = request.POST['pass']
        u = User.objects.get(username=request.user)
        if f['userID'] in u.profile.GUID:  # noqa
            try:
                API = callback(f, u, p, userID, accountID)
            except UnicodeDecodeError:  # pragma: no cover
                e = {
                "Error": [{"error_description_translated": "During decpyting something whent wrong, maybe you entreded a wrong password?"}]  # noqa
                }
                return HttpResponse(json.dumps(e))

            r = getattr(API, selector.strip('/'))()
            return HttpResponse(json.dumps(r))
        else:  # pragma: no cover
            e = {
            'Error': [{'error_description_translated': 'This file is not yours to use.'}]  # noqa
            }
            return HttpResponse(json.dumps(e))


@otp_required
def invoice_downloader(request):
    '''
    Need to mock bunq api response to test this view
    '''
    if request.method == 'GET':
        user = User.objects.get(username=request.user)
        file_path = Session.objects.get(
            session_key=user.profile.invoice_token
        ).get_decoded()['invoice_pdf']

        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type="application/force-download")  # noqa
            response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('BunqWebApp_invoice.pdf')  # noqa
            try:
                return response
            # except Exception as e:
            #     raise
            finally:
                os.remove(file_path)


@otp_required
def avatar_downloader(request):
    if request.method == 'GET':
        user = User.objects.get(username=request.user)
        file_path = Session.objects.get(
            session_key=user.profile.avatar_token
        ).get_decoded()["avatar_png"]

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="application/force-download")  # noqa
        response['Content-Disposition'] = 'attachment; filename=%s' % smart_str('BunqWebApp_avatar.png')  # noqa
        try:
            return response
        # except Exception as e:
        #     raise
        finally:
            os.remove(file_path)
