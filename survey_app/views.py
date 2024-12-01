from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from .models import Survey, Question, Option, Response, Choice
from django.contrib.auth.models import Group
from .forms import CustomUserCreationForm
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import get_user_model
from .models import Survey, Question, Response
from django.http import JsonResponse
import json
from django.db.models import Exists, OuterRef
from django.views.decorators.csrf import csrf_exempt
from datetime import date, datetime

User = get_user_model()

class CustomLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = AuthenticationForm

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)
    
    
def register(request):
    """
    Register a new user and assign roles.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            role = form.cleaned_data['role']

            if role == 'creator':
                creator_group, _ = Group.objects.get_or_create(name='creator')
                creator_group.user_set.add(user)

                user.is_staff = True
                user.save()
            else:
                taker_group, _ = Group.objects.get_or_create(name='taker')
                taker_group.user_set.add(user)
                

            login(request, user)
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()

    return render(request, 'registration/register.html', {'form': form})

@login_required
def dashboard(request):
    """
    Display surveys based on user role.
    """
    today = date.today()
    if request.user.groups.filter(name='creator').exists():
        surveys = Survey.objects.filter(creator=request.user)
    else:
        surveys = Survey.objects.filter(status__in=['published', 'republished', 'closed']).annotate(
            completed=Exists(
                Choice.objects.filter(
                    user=request.user,
                    question__survey=OuterRef('pk')
                )
            )
        )
    
    for survey in surveys:
        if survey.date_of_close: 
            if update_status_if_closed(survey.date_of_close):
                survey.status = 'closed'
            survey.time_to_close = calculate_time_to_close(survey.date_of_close)
        else:
            survey.time_to_close = "N/A"  

    return render(request, 'dashboard.html', {'surveys': surveys, 'today': today})

@login_required
def create_survey(request):
    """
    Allow creators to create a survey.
    """
    if not request.user.is_staff:  
        return redirect('dashboard')

    if request.method == 'POST':
        name = request.POST['name']
        description = request.POST['description']
        date_of_close = request.POST.get('date_of_close')



        creator = request.user 
        survey = Survey.objects.create(creator=creator, name=name, description=description, date_of_close=date_of_close)
        return redirect('edit_survey', survey_id=survey.id)

    return redirect('edit_survey', survey_id=survey.id)

def edit_survey(request, survey_id):
    survey = get_object_or_404(Survey, id=survey_id)
    survey.time_to_close = calculate_time_to_close(survey.date_of_close)
    if update_status_if_closed(survey.date_of_close):
                survey.status = 'closed'
    questions = survey.questions.all()
    today = date.today()

    if request.method == "POST":
        survey.name = request.POST.get('name', survey.name)
        survey.description = request.POST.get('description', survey.description)
        survey.status = request.POST.get('status', survey.status)
        date_of_close = request.POST.get('date_of_close')
        survey.date_of_close = date_of_close
        survey.save()
        return redirect('edit_survey', survey_id=survey.id)

    return render(request, 'edit_survey.html', {'survey': survey, 'today': today, 'questions': questions})


def add_question(request, survey_id):
    if request.method == "POST":
        try:
        
            data = json.loads(request.body)
            question_text = data.get('question_text') 
            response_texts = data.get('responses', [])  

           
            if not question_text or not response_texts:
                return JsonResponse({'success': False, 'message': 'Question text and at least one response are required.'}, status=400)

        
            survey = get_object_or_404(Survey, id=survey_id)

        
            question = Question.objects.create(survey=survey, text=question_text)

           
            for response_text in response_texts:
                if response_text.strip(): 
                    Option.objects.create(question=question, text=response_text.strip())


            return JsonResponse({'success': True, 'message': 'Question and responses added successfully.'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)


def take_survey(request, survey_id):
    """
    Allow users to take a survey or resubmit when the survey is republished.
    Updates previously submitted answers instead of creating new ones.
    """
    survey = get_object_or_404(Survey, id=survey_id)
    user_responses = {}  

    for question in survey.questions.all():
        choice = Choice.objects.filter(user=request.user, question=question).first()
        if choice:
            user_responses[question.id] = choice.option.id

    if request.method == 'POST':
        for question in survey.questions.all():
            selected_option_id = request.POST.get(f'question-{question.id}')
            if selected_option_id:
                selected_option = get_object_or_404(Option, id=selected_option_id)

                Choice.objects.update_or_create(
                    user=request.user,
                    question=question,
                    defaults={'option': selected_option}
                )

        return redirect('take_survey', survey_id=survey.id)

    question_stats = []
    for question in survey.questions.all():
        options_data = []
        total_responses = Choice.objects.filter(question=question).count()

        for option in question.options.all():
            count = Choice.objects.filter(question=question, option=option).count()
            percentage = (count / total_responses * 100) if total_responses > 0 else 0
            options_data.append({
                'option': option,
                'count': count,
                'percentage': percentage,
            })

        question_stats.append({'question': question, 'options': options_data})

    if update_status_if_closed(survey.date_of_close):
                survey.status = 'closed'
    
    return render(request, 'take_survey.html', {
        'survey': survey,
        'user_responses': user_responses,
        'submitted': bool(user_responses),  
        'question_stats': question_stats,
    })


@login_required
def survey_results(request, survey_id):
    """
    View the results of a survey (admin can see results for all surveys).
    Only staff users can view the results for a given survey.
    """
    survey = get_object_or_404(Survey, id=survey_id)

   
    if not request.user.is_staff:
        return redirect('dashboard')  

   
    questions = survey.questions.all()

   
    results = {}

    
    total_users = Choice.objects.filter(question__survey=survey).values('user').distinct().count()

   
    for question in questions:
      
        choices = Choice.objects.filter(question=question)

        
        option_counts = {}
        for choice in choices:
            option_counts[choice.option.text] = option_counts.get(choice.option.text, 0) + 1

       
        option_percentages = {option: (count / total_users) * 100 for option, count in option_counts.items()}

       
        results[question] = {
            'counts': option_counts,
            'percentages': option_percentages,
        }

    return render(request, 'survey_results.html', {
        'survey': survey,
        'results': results,
        'total_users': total_users,
    })

@login_required
def fetch_responses(request, survey_id, question_id):
    """
    Fetch responses for a given question.
    """
    try:
        survey = Survey.objects.get(id=survey_id, creator=request.user)
        question = survey.questions.get(id=question_id)
        responses = [{"id": option.id, "text": option.text} for option in question.options.all()]
        return JsonResponse({"success": True, "responses": responses})
    except Survey.DoesNotExist:
        return JsonResponse({"success": False, "message": "Survey not found."})
    except Question.DoesNotExist:
        return JsonResponse({"success": False, "message": "Question not found."})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})

@login_required
@csrf_exempt
def edit_question(request, survey_id, question_id):
    """
    Update a question and its responses.
    """
    if request.method == "POST":
        try:
            survey = Survey.objects.get(id=survey_id, creator=request.user)

            question = survey.questions.get(id=question_id)

            payload = json.loads(request.body)
            question_text = payload.get("question_text")
            responses = payload.get("responses")

            if not question_text or not responses:
                return JsonResponse({"success": False, "message": "Invalid data provided."})

            question.text = question_text
            question.save()

            question.options.all().delete()
            for response_text in responses:
                Option.objects.create(question=question, text=response_text)

            return JsonResponse({"success": True, "message": "Question and responses updated successfully."})

        except Survey.DoesNotExist:
            return JsonResponse({"success": False, "message": "Survey not found or access denied."})
        except Question.DoesNotExist:
            return JsonResponse({"success": False, "message": "Question not found."})
        except Exception as e:
            return JsonResponse({"success": False, "message": f"An error occurred: {str(e)}"})

    return JsonResponse({"success": False, "message": "Invalid request method."})


def calculate_time_to_close(date_of_close):
    today = date.today()

    if isinstance(date_of_close, datetime):
        date_of_close = date_of_close.date()
    delta = date_of_close - today

    if delta.days > 0:
        months = delta.days // 30  # Approximate number of months
        days = delta.days % 30
        if months > 0:
            return f"{months} month{'s' if months > 1 else ''}, {days} day{'s' if days != 1 else ''}"
        return f"{days} day{'s' if days != 1 else ''}"
    elif delta.days == 0:
        return "Closes Today"
    else:
        return "Closed"
    

def update_status_if_closed(date_of_close):
    today = date.today()

    if isinstance(date_of_close, datetime):
        date_of_close = date_of_close.date()
    delta = date_of_close - today

    if delta.days < 0:
        return True