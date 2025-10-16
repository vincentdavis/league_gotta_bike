from django.shortcuts import render
from django.views.generic import TemplateView


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
