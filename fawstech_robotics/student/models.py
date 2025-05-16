from django.db import models
from djongo import models  # Djongo for MongoDB
from admin_panel.models import User,MockTest
import random
from django.utils import timezone
from djongo import models
from admin_panel.models import User, Course,Quiz
from bson.decimal128 import Decimal128
from bson import Decimal128  #

# student/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    dob = models.DateField(blank=True, null=True)
    institution = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='student_profiles/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

class EmailOTP(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="email_otp")
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    def generate_otp(self):
        return str(random.randint(100000, 999999))

    def is_expired(self):
        now = timezone.now()
        diff = now - self.created_at

    # Debugging output
        print("DEBUG: Current time (timezone.now()):", now)
        print("DEBUG: OTP created_at:", self.created_at)
        print("DEBUG: Time difference in seconds:", diff.total_seconds())

        return diff.total_seconds() > 300  # 5 minutes


class LearningPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="learning_preference")
    
    top_learning_goal = models.CharField(max_length=255)
    learning_style = models.CharField(max_length=255)
    motivation = models.CharField(max_length=255)
    daily_learning_goal = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.user.email}'s Learning Preferences"

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email
    
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'course')  # prevent duplicate course in cart

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    razorpay_order_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    direct_buy = models.BooleanField(default=False)  # true for Buy Now, false for cart
    
    def save(self, *args, **kwargs):
        if isinstance(self.amount, Decimal128):
            self.amount = self.amount.to_decimal()
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

class Payment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    razorpay_payment_id = models.CharField(max_length=255)
    razorpay_signature = models.CharField(max_length=255)
    paid_at = models.DateTimeField(auto_now_add=True)

class PurchasedCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='purchased_courses')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')

from djongo import models
from admin_panel.models import User, Course, Chapter

from djongo import models
from django.core.exceptions import ValidationError
from admin_panel.models import User, Course

class CourseProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='progress')
    completed_chapters = models.JSONField(default=list)
    completed_quizzes = models.JSONField(default=list)  # Ensure default is list
    progress = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if not all(isinstance(id, int) for id in self.completed_chapters):
            raise ValidationError("completed_chapters must contain only integers")
        if not all(isinstance(id, int) for id in self.completed_quizzes):
            raise ValidationError("completed_quizzes must contain only integers")

    def save(self, *args, **kwargs):
        # Handle None for completed_chapters and completed_quizzes
        self.completed_chapters = list(set(self.completed_chapters or []))
        self.completed_quizzes = list(set(self.completed_quizzes or []))
        self.clean()
        total_chapters = self.course.total_chapters
        total_quizzes = self.course.total_quizzes
        total_items = total_chapters + total_quizzes
        if total_items == 0:
            self.progress = 0.0
        else:
            video_weight = 0.7 / max(total_chapters, 1)
            quiz_weight = 0.3 / max(total_quizzes, 1)
            self.progress = round(
                (len(self.completed_chapters) * video_weight * 100) +
                (len(self.completed_quizzes) * quiz_weight * 100),
                2
            )
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('user', 'course')
        indexes = [
            models.Index(fields=['user', 'course']),
        ]
    
class QuizAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    selected_option = models.IntegerField()  # 1, 2, 3, or 4
    is_correct = models.BooleanField()
    attempted_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Validate selected_option is 1–4
        if self.selected_option not in [1, 2, 3, 4]:
            raise ValidationError("Selected option must be 1, 2, 3, or 4")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('user', 'quiz')  # One attempt per user per quiz
        indexes = [
            models.Index(fields=['user', 'quiz']),
        ]

    def __str__(self):
        return f"{self.user.email} - Quiz {self.quiz.id} ({'Correct' if self.is_correct else 'Incorrect'})"
    
class MockTestAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mock_test_attempts')
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='attempts')
    answers = models.JSONField(default=list)  # List of {"quiz_id": <id>, "selected_option": <1-4>}
    score = models.IntegerField(default=0)  # Total correct answers
    total_questions = models.IntegerField(default=0)  # Total questions in mock test
    start_time = models.DateTimeField()  # When attempt started
    end_time = models.DateTimeField()  # When attempt submitted
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        # Validate answers format
        if not isinstance(self.answers, list):
            raise ValidationError("Answers must be a list")
        for answer in self.answers:
            if not isinstance(answer, dict) or 'quiz_id' not in answer or 'selected_option' not in answer:
                raise ValidationError("Each answer must have quiz_id and selected_option")
            if not isinstance(answer['selected_option'], int) or not 1 <= answer['selected_option'] <= 4:
                raise ValidationError("Selected option must be 1, 2, 3, or 4")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('user', 'mock_test')
        indexes = [
            models.Index(fields=['user', 'mock_test']),
        ]

