from django.db import models
from django.contrib.auth.models import User

# Survey model
class Survey(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('republished', 'Republished'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_surveys',  
    )
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    date_of_close = models.DateTimeField(null=True, blank=True)  # New field

    def __str__(self):
        return self.name


# Question model
class Question(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='questions',  
    )
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


# Option model
class Option(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',  
    )
    text = models.CharField(max_length=255)

    def __str__(self):
        return self.text


# Response model
class Response(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name='responses', 
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='responses', 
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Response from {self.user.username} for {self.survey.name}"


# Choice model
class Choice(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, null=True, on_delete=models.CASCADE)
    option = models.ForeignKey(Option, null=True, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.user} chose {self.option.text} for question: {self.question.text}"
