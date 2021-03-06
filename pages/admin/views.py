# -*- coding: utf-8 -*-
"""Pages admin views"""
from pages import settings
from pages.models import Page, Content
from pages.utils import get_placeholders
from pages.phttp import get_language_from_request
from pages.permissions import PagePermission

from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def change_status(request, page_id):
    """
    Switch the status of a page.
    """
    perm = PagePermission(request.user).check('change', method='POST')
    if perm and request.method == 'POST':
        page = Page.objects.get(pk=page_id)
        page.status = int(request.POST['status'])
        page.invalidate()
        page.save()
        return HttpResponse(str(page.status))
    raise Http404
change_status = staff_member_required(change_status)

def list_pages_ajax(request, invalid_move=False):
    """Render pages table for ajax function."""
    language = get_language_from_request(request)
    pages = Page.objects.root()
    perms = PagePermission(request.user)
    context = {
        'can_publish': perms.check('publish'),
        'invalid_move':invalid_move,
        'language': language,
        'pages': pages,
    }
    return render_to_response("admin/pages/page/change_list_table.html", 
        context,
        context_instance=RequestContext(request))
list_pages_ajax = staff_member_required(list_pages_ajax)

@csrf_exempt
def modify_content(request, page_id, content_type, language_id):
    """Modify the content of a page."""
    page = get_object_or_404(Page, pk=page_id)
    perm = PagePermission(request.user).check('change', page=page,
            lang=language_id, method='POST')
    if perm and request.method == 'POST':
        content = request.POST.get('content', False)
        if not content:
            raise Http404
        page = Page.objects.get(pk=page_id)
        if settings.PAGE_CONTENT_REVISION:
            Content.objects.create_content_if_changed(page, language_id,
                                                      content_type, content)
        else:
            Content.objects.set_or_create_content(page, language_id,
                                                  content_type, content)
        page.invalidate()
        # to update last modification date
        page.save()

        return HttpResponse('ok')
    raise Http404
modify_content = staff_member_required(modify_content)

@csrf_exempt
def delete_content(request, page_id, language_id):
    page = get_object_or_404(Page, pk=page_id)
    perm = PagePermission(request.user).check('delete', page=page,
            lang=language_id, method='POST')
    if not perm:
        raise Http404

    for c in Content.objects.filter(page=page, language=language_id):
        c.delete()

    destination = request.REQUEST.get('next', request.META.get('HTTP_REFERER',
        '/admin/pages/page/%s/' % page_id))
    return HttpResponseRedirect(destination)
delete_content = staff_member_required(delete_content)

def traduction(request, page_id, language_id):
    """Traduction helper."""
    page = Page.objects.get(pk=page_id)
    lang = language_id
    placeholders = get_placeholders(page.get_template())
    language_error = (
        Content.objects.get_content(page, language_id, "title")
        is None
    )
    return render_to_response('pages/traduction_helper.html', {
        'page':page,
        'lang':lang,
        'language_error':language_error,
        'placeholders':placeholders,
    }, context_instance=RequestContext(request))
traduction = staff_member_required(traduction)

def get_content(request, page_id, content_id):
    """Get the content for a particular page"""
    content = Content.objects.get(pk=content_id)
    return HttpResponse(content.body)
get_content = staff_member_required(get_content)

@csrf_exempt
def move_page(request, page_id, extra_context=None):
    """Move the page to the requested target, at the given
    position."""
    page = Page.objects.get(pk=page_id)

    target = request.POST.get('target', None)
    position = request.POST.get('position', None)
    if target is not None and position is not None:
        try:
            target = Page.objects.get(pk=target)
        except Page.DoesNotExist:
            pass
            # TODO: should use the django message system
            # to display this message
            # _('Page could not been moved.')
        else:
            # move_to invalidates cache on a model level
            from mptt.exceptions import InvalidMove
            invalid_move = False
            try:
                page.move_to(target, position)
            except InvalidMove:
                invalid_move = True
            return list_pages_ajax(request, invalid_move)
    return HttpResponseRedirect('../../')

def sub_menu(request, page_id):
    """Render the children of the requested page with the sub_menu
    template."""
    page = Page.objects.get(id=page_id)
    pages = page.children.all()
    page_languages = settings.PAGE_LANGUAGES
    perms = PagePermission(request.user)
    return render_to_response("admin/pages/page/sub_menu.html", {
        'can_publish': perms.check('publish'),
        'page':page,
        'pages':pages,
        'page_languages':page_languages,
    },        context_instance=RequestContext(request))
sub_menu = staff_member_required(sub_menu)
