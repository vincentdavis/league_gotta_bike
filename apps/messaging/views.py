from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, DetailView
from django.http import HttpResponseForbidden

from .models import ChatRoom


class ChatRoomView(TemplateView):
    """
    Public chat room view.
    Anyone can access and participate in the chat.
    """
    template_name = 'messaging/chat_room.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Public Chat Room'
        return context


class ChatRoomDetailView(LoginRequiredMixin, DetailView):
    """
    View for individual chat room.
    """
    model = ChatRoom
    template_name = 'messaging/chat_room_detail.html'
    context_object_name = 'room'

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to access this room."""
        self.object = self.get_object()

        if not self.object.can_user_access(request.user):
            return HttpResponseForbidden("You don't have permission to access this chat room.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        return context
