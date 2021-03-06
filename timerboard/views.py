import datetime

from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

from util import check_if_user_has_permission
from authentication.managers import AuthServicesInfoManager
from eveonline.managers import EveManager
from form import TimerForm
from models import Timer


import logging

logger = logging.getLogger(__name__)

def timer_util_test(user):
    return check_if_user_has_permission(user, 'member') or check_if_user_has_permission(user, 'blue_member')


@login_required
@user_passes_test(timer_util_test)
@permission_required('auth.timer_view')
def timer_view(request):
    logger.debug("timer_view called by user %s" % request.user)
    auth_info = AuthServicesInfoManager.get_auth_service_info(request.user)
    char = EveManager.get_character_by_id(auth_info.main_char_id)
    if char:
        corp = EveManager.get_corporation_info_by_id(char.corporation_id)
    else:
        corp = None
    if corp:
        corp_timers = Timer.objects.all().filter(corp_timer=True).filter(eve_corp=corp)
    else:
        corp_timers = []
    timer_list = Timer.objects.filter(corp_timer=False)
    closest_timer = None
    if timer_list:
        closest_timer = \
        sorted(list(Timer.objects.all().filter(corp_timer=False)), key=lambda d:  (timezone.now()))[0]
    logger.debug("Determined closest timer is %s" % closest_timer)
    render_items = {'timers': Timer.objects.all().filter(corp_timer=False),
                    'corp_timers': corp_timers,
                    'closest_timer': closest_timer}

    return render_to_response('registered/timermanagement.html', render_items, context_instance=RequestContext(request))


@login_required
@permission_required('auth.timer_management')
def add_timer_view(request):
    logger.debug("add_timer_view called by user %s" % request.user)
    if request.method == 'POST':
        form = TimerForm(request.POST)
        logger.debug("Request type POST contains form valid: %s" % form.is_valid())
        if form.is_valid():
            # Get character
            auth_info = AuthServicesInfoManager.get_auth_service_info(request.user)
            character = EveManager.get_character_by_id(auth_info.main_char_id)
            corporation = EveManager.get_corporation_info_by_id(character.corporation_id)
            logger.debug("Determined timer add request on behalf of character %s corporation %s" % (character, corporation))
            # calculate future time
            future_time = datetime.timedelta(days=form.cleaned_data['days_left'], hours=form.cleaned_data['hours_left'], minutes=form.cleaned_data['minutes_left'])
            current_time = timezone.now()
            eve_time = current_time + future_time
            logger.debug("Determined timer eve time is %s - current time %s, adding %s" % (eve_time, current_time, future_time))
            # handle valid form
            timer = Timer()
            timer.details = form.cleaned_data['details']
            timer.system = form.cleaned_data['system']
            timer.planet_moon = form.cleaned_data['planet_moon']
            timer.structure = form.cleaned_data['structure']
            timer.objective = form.cleaned_data['objective']
            timer.eve_time = eve_time
            timer.important = form.cleaned_data['important']
            timer.corp_timer = form.cleaned_data['corp_timer']
            timer.eve_character = character
            timer.eve_corp = corporation
            timer.user = request.user
            timer.save()
            logger.info("Created new timer in %s at %s by user %s" % (timer.system, timer.eve_time, request.user))
            return HttpResponseRedirect("/timers/")
    else:
        logger.debug("Returning new TimerForm")
        form = TimerForm()

    render_items = {'form': form}

    return render_to_response('registered/addtimer.html', render_items, context_instance=RequestContext(request))


@login_required
@permission_required('auth.timer_management')
def remove_timer(request, timer_id):
    logger.debug("remove_timer called by user %s for timer id %s" % (request.user, timer_id))
    if Timer.objects.filter(id=timer_id).exists():
        timer = Timer.objects.get(id=timer_id)
        timer.delete()
        logger.debug("Deleting timer id %s by user %s" % (timer_id, request.user))
    else:
        logger.error("Unable to delete timer id %s for user %s - timer matching id not found." % (timer_id, request.user))
    return HttpResponseRedirect("/timers/")


@login_required
@permission_required('auth.timer_management')
def edit_timer(request, timer_id):
    logger.debug("edit_timer called by user %s for timer id %s" % (request.user, timer_id))
    timer = get_object_or_404(Timer, id=timer_id)
    if request.method == 'POST':
        form = TimerForm(request.POST)
        logger.debug("Received POST request containing updated timer form, is valid: %s" % form.is_valid())
        if form.is_valid():
            auth_info = AuthServicesInfoManager.get_auth_service_info(request.user)
            character = EveManager.get_character_by_id(auth_info.main_char_id)
            corporation = EveManager.get_corporation_info_by_id(character.corporation_id)
            logger.debug("Determined timer edit request on behalf of character %s corporation %s" % (character, corporation))
            # calculate future time
            future_time = datetime.timedelta(days=form.cleaned_data['days_left'], hours=form.cleaned_data['hours_left'], minutes=form.cleaned_data['minutes_left'])
            current_time = datetime.datetime.utcnow()
            eve_time = current_time + future_time
            logger.debug("Determined timer eve time is %s - current time %s, adding %s" % (eve_time, current_time, future_time))
            timer.details = form.cleaned_data['details']
            timer.system = form.cleaned_data['system']
            timer.planet_moon = form.cleaned_data['planet_moon']
            timer.structure = form.cleaned_data['structure']
            timer.objective = form.cleaned_data['objective']
            timer.eve_time = eve_time
            timer.important = form.cleaned_data['important']
            timer.corp_timer = form.cleaned_data['corp_timer']
            timer.eve_character = character
            timer.eve_corp = corporation
            logger.info("User %s updating timer id %s " % (request.user, timer_id))
            timer.save()

        logger.debug("Detected no changes between timer id %s and supplied form." % timer_id)
        return HttpResponseRedirect("/timers/")
    else:
        current_time = timezone.now()
        td = timer.eve_time - current_time
        tddays, tdhours, tdminutes = td.days, td.seconds // 3600, td.seconds // 60 % 60
        data = {
            'details': timer.details,
            'system': timer.system,
            'planet_moon': timer.planet_moon,
            'structure': timer.structure,
            'objective': timer.objective,
            'important': timer.important,
            'corp_timer': timer.corp_timer,
            'days_left': tddays,
            'hours_left': tdhours,
            'minutes_left': tdminutes,

        }
        form = TimerForm(initial= data)
    return render_to_response('registered/timerupdate.html', {'form':form}, context_instance=RequestContext(request))
