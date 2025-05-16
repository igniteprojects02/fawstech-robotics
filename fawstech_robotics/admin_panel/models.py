from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from djongo import models
from bson import Decimal128
import os
import logging

logger = logging.getLogger(__name__)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, role="STUDENT"):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        return self.create_user(email, password, role="ADMIN")

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('STUDENT', 'Student'),
        ('ADMIN', 'Admin'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='STUDENT')
    is_active = models.BooleanField(default=True)

    groups = models.ManyToManyField(Group, related_name="custom_user_groups", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="custom_user_permissions", blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'

class Author(models.Model):
    name = models.CharField(max_length=100)
    domain = models.CharField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    profile_picture = models.ImageField(upload_to='author_profiles/', null=True, blank=True)
    expertise = models.CharField(max_length=255, null=True, blank=True)
    occupation = models.CharField(max_length=100, null=True, blank=True)
    experience_in_years = models.PositiveIntegerField(null=True, blank=True)
    professional_experience = models.TextField(null=True, blank=True)
    education_and_teaching = models.TextField(null=True, blank=True)
    author_and_content_creator = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.profile_picture and os.path.isfile(self.profile_picture.path):
            os.remove(self.profile_picture.path)
        super().delete(*args, **kwargs)

class LandingMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('IMAGE', 'Image'),
        ('VIDEO', 'Video'),
    ]

    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(upload_to='landing_media/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.media_type} - {self.file.name}"
    
    def delete(self, *args, **kwargs):
        if self.file and os.path.isfile(self.file.path):
            os.remove(self.file.path)
        super().delete(*args, **kwargs)

class GalleryImage(models.Model):
    file = models.ImageField(upload_to='gallery/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name

class Course(models.Model):
    thumbnail = models.ImageField(upload_to='course_thumbnails/')
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    author = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    what_you_will_learn_1 = models.CharField(max_length=255, null=True, blank=True)
    what_you_will_learn_2 = models.CharField(max_length=255, null=True, blank=True)
    what_you_will_learn_3 = models.CharField(max_length=255, null=True, blank=True)
    what_you_will_learn_4 = models.CharField(max_length=255, null=True, blank=True)
    what_you_will_learn_5 = models.CharField(max_length=255, null=True, blank=True)
    what_you_will_learn_6 = models.CharField(max_length=255, null=True, blank=True)
    price_inr = models.DecimalField(max_digits=10, decimal_places=2)
    offer_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recommended = models.BooleanField(default=False)
    position = models.IntegerField(null=True, blank=True)
    total_chapters = models.IntegerField(default=0)
    total_quizzes = models.IntegerField(default=0)
    why_choose_this_course = models.TextField(null=True, blank=True)
    what_will_you_learn = models.TextField(null=True, blank=True)
    is_course_updated = models.TextField(null=True, blank=True)
    who_is_this_course_for = models.TextField(null=True, blank=True)
    course_requirements = models.TextField(null=True, blank=True)

    def update_total_chapters(self):
        try:
            total = sum(module.total_chapters for module in self.modules.all())
            self.total_chapters = total
            super().save(update_fields=['total_chapters'])
        except Exception as e:
            logger.error(f"Error updating total_chapters for Course {self.id}: {e}")
            raise

    def update_total_quizzes(self):
        try:
            total = sum(
                chapter.quizzes.count()
                for module in self.modules.all()
                for chapter in module.chapters.all()
            )
            self.total_quizzes = total
            super().save(update_fields=['total_quizzes'])
        except Exception as e:
            logger.error(f"Error updating total_quizzes for Course {self.id}: {e}")
            raise

    def save(self, *args, **kwargs):
        try:
            if isinstance(self.price_inr, Decimal128):
                self.price_inr = self.price_inr.to_decimal()
            if self.offer_price is not None and isinstance(self.offer_price, Decimal128):
                self.offer_price = self.offer_price.to_decimal()
            super().save(*args, **kwargs)
            self.update_total_chapters()
            self.update_total_quizzes()
        except Exception as e:
            logger.error(f"Error saving Course {self.id}: {e}")
            raise

    def __str__(self):
        return self.name

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    module_name = models.CharField(max_length=200)
    total_chapters = models.IntegerField(default=0)

    def update_total_chapters(self):
        try:
            total = self.chapters.count()
            self.total_chapters = total
            super().save(update_fields=['total_chapters'])
            self.course.update_total_chapters()
        except Exception as e:
            logger.error(f"Error updating total_chapters for Module {self.id}: {e}")
            raise

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.update_total_chapters()

    def __str__(self):
        return f"{self.course.name} - {self.module_name}"

    def delete(self, *args, **kwargs):
        for chapter in self.chapters.all():
            chapter.delete()
        super().delete(*args, **kwargs)

class Chapter(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='chapters')
    chapter_name = models.CharField(max_length=200)
    chapter_description = models.TextField(null=True, blank=True)
    video = models.FileField(upload_to='chapter_videos/')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.module.update_total_chapters()

    def delete(self, *args, **kwargs):
        if self.video and os.path.isfile(self.video.path):
            os.remove(self.video.path)
        module = self.module
        super().delete(*args, **kwargs)
        module.update_total_chapters()

    def __str__(self):
        return f"{self.module.module_name} - {self.chapter_name}"

class Quiz(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='quizzes')
    question = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    correct_option = models.IntegerField(choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.chapter.module.course.update_total_quizzes()

    def delete(self, *args, **kwargs):
        course = self.chapter.module.course
        super().delete(*args, **kwargs)
        course.update_total_quizzes()

    def __str__(self):
        return f"Quiz: {self.question[:30]}..."

class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='event_images/')
    event_date = models.DateField()

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        super().delete(*args, **kwargs)

class MockTest(models.Model):
    heading = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='mock_tests/')
    created_at = models.DateTimeField(auto_now_add=True)
    duration = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return self.heading

class MockTestQuiz(models.Model):
    mock_test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='quizzes')
    question = models.TextField()
    option_1 = models.CharField(max_length=255)
    option_2 = models.CharField(max_length=255)
    option_3 = models.CharField(max_length=255)
    option_4 = models.CharField(max_length=255)
    correct_option = models.IntegerField(choices=[(1, "Option 1"), (2, "Option 2"), (3, "Option 3"), (4, "Option 4")])

    def __str__(self):
        return self.question[:50]