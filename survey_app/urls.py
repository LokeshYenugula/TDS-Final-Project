from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('register/', views.register, name='register'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='/login/'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create/', views.create_survey, name='create_survey'),
    path('survey/<int:survey_id>/add-question/', views.add_question, name='add_question'),
    path('survey/<int:survey_id>/edit/', views.edit_survey, name='edit_survey'),
    path('take/<int:survey_id>/', views.take_survey, name='take_survey'),
    path('results/<int:survey_id>/', views.survey_results, name='survey_results'),
    path("survey/<int:survey_id>/question/<int:question_id>/responses/", views.fetch_responses, name="fetch_responses"),
    path("survey/<int:survey_id>/edit-question/<int:question_id>/", views.edit_question, name="edit_question"),
]
