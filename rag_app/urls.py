from django.urls import path
from . import views

urlpatterns = [
    # Pages
    path("",                views.index,     name="index"),
    path("chat/",           views.chat,      name="chat"),
    path("documents/",      views.documents, name="documents"),

    # Authentication
    path("signup/",         views.signup_page,  name="signup_page"),
    path("login/",           views.login_page,   name="login_page"),
    path("api/signup/",      views.signup_user,  name="signup"),
    path("api/login/",       views.login_user,   name="login"),
    path("logout/",          views.logout_user,  name="logout"),

    # Documents API
    path("api/documents/upload/",       views.upload_document,  name="upload"),
    path("api/documents/",              views.list_documents,   name="documents_api"),
    path("api/documents/<int:doc_id>/", views.delete_document,  name="delete_document"),

    # Sessions API
    path("api/sessions/",               views.create_session,   name="create_session"),
    path("api/sessions/list/",          views.list_sessions,    name="list_sessions"),
    path("api/sessions/<str:session_id>/messages/", views.get_messages, name="get_messages"),

    # Chat API
    path("api/ask/",                    views.ask_question,     name="ask"),

    path("api/sessions/<str:session_id>/clear/",  views.clear_session_messages, name="clear_session"),
    path("api/sessions/<str:session_id>/delete/", views.delete_session,         name="delete_session"),
]