from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth import password_validation
from admin_panel.models import User, Course, Module, Chapter, Author
from admin_panel.utils import get_video_duration
from .utils import get_video_duration1, calculate_course_duration
from .models import (Student, LearningPreference, NewsletterSubscriber, CartItem, 
                     Cart, OrderItem, PurchasedCourse, CourseProgress, QuizAttempt,EmailOTP)
from admin_panel.models import MockTest, MockTestQuiz, Quiz
from student.models import MockTestAttempt
import os
import random
from django.contrib.auth import get_user_model
import json
from django.utils import timezone

class AuthorSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()
    course_names = serializers.SerializerMethodField()
    professional_experience = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    education_and_teaching = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    author_and_content_creator = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Author
        fields = [
            'id', 'name', 'domain', 'description', 'profile_picture', 'course_names',
            'expertise', 'occupation', 'experience_in_years', 'professional_experience',
            'education_and_teaching', 'author_and_content_creator', 'created_at', 'updated_at'
        ]

    def validate_list_field(self, value, field_name):
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError(f"{field_name} must be a list of strings")
            for item in value:
                if not isinstance(item, str):
                    raise serializers.ValidationError(f"Each {field_name.lower()} entry must be a string")
                if len(item.strip()) == 0:
                    raise serializers.ValidationError(f"{field_name} entries cannot be empty")
        return value

    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else None
        return None

    def get_course_names(self, obj):
        return [course.name for course in obj.courses.all()]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.profile_picture and hasattr(instance.profile_picture, 'url'):
            representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url) if request else None
        else:
            representation['profile_picture'] = None

        if instance.professional_experience:
            if isinstance(instance.professional_experience, str):
                try:
                    representation['professional_experience'] = json.loads(instance.professional_experience)
                except json.JSONDecodeError:
                    representation['professional_experience'] = None
            elif isinstance(instance.professional_experience, list):
                representation['professional_experience'] = instance.professional_experience
            else:
                representation['professional_experience'] = None
        else:
            representation['professional_experience'] = None

        if instance.education_and_teaching:
            if isinstance(instance.education_and_teaching, str):
                try:
                    representation['education_and_teaching'] = json.loads(instance.education_and_teaching)
                except json.JSONDecodeError:
                    representation['education_and_teaching'] = None
            elif isinstance(instance.education_and_teaching, list):
                representation['education_and_teaching'] = instance.education_and_teaching
            else:
                representation['education_and_teaching'] = None
        else:
            representation['education_and_teaching'] = None

        if instance.author_and_content_creator:
            if isinstance(instance.author_and_content_creator, str):
                try:
                    representation['author_and_content_creator'] = json.loads(instance.author_and_content_creator)
                except json.JSONDecodeError:
                    representation['author_and_content_creator'] = None
            elif isinstance(instance.author_and_content_creator, list):
                representation['author_and_content_creator'] = instance.author_and_content_creator
            else:
                representation['author_and_content_creator'] = None
        else:
            representation['author_and_content_creator'] = None

        return representation

class StudentSignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(max_length=15)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email is already registered.")
        return value

    def validate_phone_number(self, value):
        # Check if phone number already exists in the Student model
        if Student.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number is already registered.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            role='STUDENT'
        )
        Student.objects.create(
            user=user,
            full_name=validated_data['full_name'],
            phone_number=validated_data['phone_number']
        )
        # Generate and store OTP
        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp = otp_obj.generate_otp()
        otp_obj.otp = otp
        otp_obj.created_at = timezone.now()
        otp_obj.is_verified = False
        otp_obj.save()
        return user, otp  # Return user and OTP for view to use

class StudentLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(email=data['email'], password=data['password'])
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        if user.role != 'STUDENT':
            raise serializers.ValidationError("Only students can log in here.")
        data['user'] = user
        return data

class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

class ForgotPasswordOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    new_password = serializers.CharField(write_only=True, min_length=6)

User = get_user_model()

# Serializer for LearningPreference
class LearningPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPreference
        fields = ['top_learning_goal', 'learning_style', 'motivation', 'daily_learning_goal']
        read_only_fields = ['user']

    def validate(self, attrs):
        # Ensure all fields are provided and not empty
        for field in ['top_learning_goal', 'learning_style', 'motivation', 'daily_learning_goal']:
            if not attrs.get(field):
                raise serializers.ValidationError({field: "This field cannot be empty."})
        return attrs
    
class NewsletterSubscriberSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsletterSubscriber
        fields = ['email']

class StudentProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'full_name', 'email', 'phone_number', 'dob',
            'institution', 'location', 'role',
            'start_date', 'end_date', 'profile_picture', 'is_phone_verified'
        ]

    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else None
        return None

class ProfilePictureSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['profile_picture', 'profile_picture_url']

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else None
        return None

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({"old_password": "Old password is incorrect"})
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match"})
        password_validation.validate_password(data['new_password'], user=user)
        return data

class StudentCourseListSerializer(serializers.ModelSerializer):
    real_price = serializers.DecimalField(source='price_inr', max_digits=10, decimal_places=2)
    number_of_modules = serializers.SerializerMethodField()
    total_duration_minutes = serializers.SerializerMethodField()
    total_duration_hours = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'thumbnail', 'description', 'author',
            'real_price', 'offer_price', 'number_of_modules',
            'total_duration_minutes', 'total_duration_hours',
        ]

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.thumbnail and hasattr(obj.thumbnail, 'url'):
            return request.build_absolute_uri(obj.thumbnail.url) if request else None
        return None

    def get_number_of_modules(self, obj):
        return obj.modules.count()

    def get_total_duration_minutes(self, obj):
        total_duration = 0
        for module in obj.modules.all():
            for chapter in module.chapters.all():
                if chapter.video and chapter.video.path and os.path.exists(chapter.video.path):
                    total_duration += get_video_duration(chapter.video.path)
        return round(total_duration, 2)

    def get_total_duration_hours(self, obj):
        total_minutes = self.get_total_duration_minutes(obj)
        return round(total_minutes / 60, 2)

class ChapterDetailSerializer(serializers.ModelSerializer):
    duration_minutes = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ['id', 'chapter_name', 'chapter_description', 'duration_minutes', 'duration_hours', 'video_url']

    def get_duration_minutes(self, obj):
        if obj.video and obj.video.path and os.path.exists(obj.video.path):
            return round(get_video_duration1(obj.video.path), 2)
        return 0

    def get_duration_hours(self, obj):
        minutes = self.get_duration_minutes(obj)
        return round(minutes / 60, 2)

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video and hasattr(obj.video, 'url'):
            return request.build_absolute_uri(obj.video.url) if request else None
        return None

class ModuleDetailSerializer(serializers.ModelSerializer):
    number_of_chapters = serializers.SerializerMethodField()
    total_duration_minutes = serializers.SerializerMethodField()
    total_duration_hours = serializers.SerializerMethodField()
    chapters = ChapterDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'module_name', 'number_of_chapters', 'total_duration_minutes', 'total_duration_hours', 'chapters']

    def get_number_of_chapters(self, obj):
        return obj.total_chapters

    def get_total_duration_minutes(self, obj):
        total = 0
        for chapter in obj.chapters.all():
            if chapter.video and chapter.video.path and os.path.exists(chapter.video.path):
                total += get_video_duration1(chapter.video.path)
        return round(total, 2)

    def get_total_duration_hours(self, obj):
        return round(self.get_total_duration_minutes(obj) / 60, 2)

class CourseDetailSerializer(serializers.ModelSerializer):
    number_of_modules = serializers.SerializerMethodField()
    number_of_chapters = serializers.SerializerMethodField()
    modules = ModuleDetailSerializer(many=True, read_only=True)
    purchased = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    what_will_you_learn = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    who_is_this_course_for = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    course_requirements = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_course_updated = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Course
        fields = [
            'id', 'thumbnail', 'name', 'description', 'category', 'author',
            'what_you_will_learn_1', 'what_you_will_learn_2', 'what_you_will_learn_3',
            'what_you_will_learn_4', 'what_you_will_learn_5', 'what_you_will_learn_6',
            'price_inr', 'offer_price', 'recommended', 'position', 'modules', 'total_chapters',
            'total_quizzes', 'why_choose_this_course', 'what_will_you_learn', 'is_course_updated',
            'who_is_this_course_for', 'course_requirements', 'number_of_modules', 'number_of_chapters', 'purchased'
        ]

    def get_number_of_modules(self, obj):
        return obj.modules.count()

    def get_number_of_chapters(self, obj):
        return obj.total_chapters

    def get_purchased(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return PurchasedCourse.objects.filter(user=user, course=obj).exists()
        return False

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['number_of_modules'] = self.get_number_of_modules(instance)
        rep['number_of_chapters'] = self.get_number_of_chapters(instance)
        rep['purchased'] = self.get_purchased(instance)

        # Handle what_will_you_learn
        if instance.what_will_you_learn:
            if isinstance(instance.what_will_you_learn, str):
                try:
                    rep['what_will_you_learn'] = json.loads(instance.what_will_you_learn)
                except json.JSONDecodeError:
                    rep['what_will_you_learn'] = None
            elif isinstance(instance.what_will_you_learn, list):
                rep['what_will_you_learn'] = instance.what_will_you_learn
            else:
                rep['what_will_you_learn'] = None
        else:
            rep['what_will_you_learn'] = None

        # Handle who_is_this_course_for
        if instance.who_is_this_course_for:
            if isinstance(instance.who_is_this_course_for, str):
                try:
                    rep['who_is_this_course_for'] = json.loads(instance.who_is_this_course_for)
                except json.JSONDecodeError:
                    rep['who_is_this_course_for'] = None
            elif isinstance(instance.who_is_this_course_for, list):
                rep['who_is_this_course_for'] = instance.who_is_this_course_for
            else:
                rep['who_is_this_course_for'] = None
        else:
            rep['who_is_this_course_for'] = None

        # Handle course_requirements
        if instance.course_requirements:
            if isinstance(instance.course_requirements, str):
                try:
                    rep['course_requirements'] = json.loads(instance.course_requirements)
                except json.JSONDecodeError:
                    rep['course_requirements'] = None
            elif isinstance(instance.course_requirements, list):
                rep['course_requirements'] = instance.course_requirements
            else:
                rep['course_requirements'] = None
        else:
            rep['course_requirements'] = None

        return rep

class CartItemSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.name', read_only=True)
    course_price = serializers.DecimalField(source='course.offer_price', max_digits=10, decimal_places=2, read_only=True)
    thumbnail = serializers.SerializerMethodField()
    description = serializers.CharField(source='course.description', read_only=True)
    author_name = serializers.CharField(source='course.author.name', read_only=True)
    price = serializers.DecimalField(source='course.price_inr', max_digits=10, decimal_places=2, read_only=True)
    offer_price = serializers.DecimalField(source='course.offer_price', max_digits=10, decimal_places=2, read_only=True)
    number_of_modules = serializers.SerializerMethodField()
    number_of_chapters = serializers.IntegerField(source='course.total_chapters', read_only=True)
    course_duration = serializers.SerializerMethodField()
    category = serializers.CharField(source='course.category', read_only=True)

    class Meta:
        model = CartItem
        fields = [
            'id', 'course', 'course_title', 'course_price', 'thumbnail',
            'description', 'author_name', 'price', 'offer_price',
            'number_of_modules', 'number_of_chapters', 'course_duration',
            'category', 'added_at'
        ]

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.course.thumbnail and hasattr(obj.course.thumbnail, 'url'):
            return request.build_absolute_uri(obj.course.thumbnail.url) if request else None
        return None

    def get_number_of_modules(self, obj):
        return obj.course.modules.count()

    def get_course_duration(self, obj):
        total_minutes = calculate_course_duration(obj.course)
        return round(total_minutes / 60, 2)

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'created_at']

class OrderItemSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.name', read_only=True)
    price = serializers.DecimalField(source='course.offer_price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'course', 'course_name', 'price']

class CreateOrderSerializer(serializers.Serializer):
    course_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=True
    )
    direct_buy = serializers.BooleanField()

    def validate(self, attrs):
        user = self.context['request'].user
        direct_buy = attrs['direct_buy']
        course_ids = attrs.get('course_ids', [])

        if not course_ids:
            raise serializers.ValidationError("course_ids is required.")

        if not direct_buy:
            cart = getattr(user, 'cart', None)
            if not cart or not cart.items.exists():
                raise serializers.ValidationError("Cart is empty.")

        return attrs

class PaymentVerificationSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    payment_id = serializers.CharField()
    signature = serializers.CharField()

class PurchasedCourseSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.name', read_only=True)
    description = serializers.CharField(source='course.description')
    thumbnail = serializers.SerializerMethodField()
    number_of_modules = serializers.SerializerMethodField()
    number_of_chapters = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    author = AuthorSerializer(source='course.author', read_only=True)
    what_will_you_learn = serializers.CharField(source='course.what_will_you_learn', required=False, allow_null=True, allow_blank=True)
    who_is_this_course_for = serializers.CharField(source='course.who_is_this_course_for', required=False, allow_null=True, allow_blank=True)
    course_requirements = serializers.CharField(source='course.course_requirements', required=False, allow_null=True, allow_blank=True)
    is_course_updated = serializers.CharField(source='course.is_course_updated', required=False, allow_null=True, allow_blank=True)
    why_choose_this_course = serializers.CharField(source='course.why_choose_this_course', required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = PurchasedCourse
        fields = [
            'id', 'course', 'course_title', 'description', 'thumbnail',
            'number_of_modules', 'number_of_chapters', 'duration', 'author', 'purchased_at',
            'why_choose_this_course', 'what_will_you_learn', 'is_course_updated',
            'who_is_this_course_for', 'course_requirements'
        ]

    def get_thumbnail(self, obj):
        request = self.context.get('request')
        if obj.course.thumbnail and hasattr(obj.course.thumbnail, 'url'):
            return request.build_absolute_uri(obj.course.thumbnail.url) if request else None
        return None

    def get_number_of_modules(self, obj):
        return obj.course.modules.count()

    def get_number_of_chapters(self, obj):
        return obj.course.total_chapters

    def get_duration(self, obj):
        total_minutes = calculate_course_duration(obj.course)
        total_hours = round(total_minutes / 60, 2)
        return total_hours

    def to_representation(self, instance):
        rep = super().to_representation(instance)

        # Handle what_will_you_learn
        if instance.course.what_will_you_learn:
            if isinstance(instance.course.what_will_you_learn, str):
                try:
                    rep['what_will_you_learn'] = json.loads(instance.course.what_will_you_learn)
                except json.JSONDecodeError:
                    rep['what_will_you_learn'] = None
            elif isinstance(instance.course.what_will_you_learn, list):
                rep['what_will_you_learn'] = instance.course.what_will_you_learn
            else:
                rep['what_will_you_learn'] = None
        else:
            rep['what_will_you_learn'] = None

        # Handle who_is_this_course_for
        if instance.course.who_is_this_course_for:
            if isinstance(instance.course.who_is_this_course_for, str):
                try:
                    rep['who_is_this_course_for'] = json.loads(instance.course.who_is_this_course_for)
                except json.JSONDecodeError:
                    rep['who_is_this_course_for'] = None
            elif isinstance(instance.course.who_is_this_course_for, list):
                rep['who_is_this_course_for'] = instance.course.who_is_this_course_for
            else:
                rep['who_is_this_course_for'] = None
        else:
            rep['who_is_this_course_for'] = None

        # Handle course_requirements
        if instance.course.course_requirements:
            if isinstance(instance.course.course_requirements, str):
                try:
                    rep['course_requirements'] = json.loads(instance.course.course_requirements)
                except json.JSONDecodeError:
                    rep['course_requirements'] = None
            elif isinstance(instance.course.course_requirements, list):
                rep['course_requirements'] = instance.course.course_requirements
            else:
                rep['course_requirements'] = None
        else:
            rep['course_requirements'] = None

        return rep

class CourseProgressSerializer(serializers.ModelSerializer):
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    completed_chapters = serializers.ListField(child=serializers.IntegerField())
    completed_quizzes = serializers.ListField(child=serializers.IntegerField())

    class Meta:
        model = CourseProgress
        fields = ['course', 'completed_chapters', 'completed_quizzes', 'progress']

    def validate_completed_chapters(self, value):
        if not all(isinstance(id, int) for id in value):
            raise serializers.ValidationError("All chapter IDs must be integers")
        return value

    def validate_completed_quizzes(self, value):
        if not all(isinstance(id, int) for id in value):
            raise serializers.ValidationError("All quiz IDs must be integers")
        return value

class CourseWithProgressSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    number_of_modules = serializers.SerializerMethodField()
    number_of_chapters = serializers.SerializerMethodField()
    chapters_completed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id', 'name', 'thumbnail', 'description', 'offer_price',
            'progress', 'updated_at', 'number_of_modules', 'number_of_chapters',
            'chapters_completed',
        ]

    def get_progress(self, obj):
        user = self.context['request'].user
        try:
            progress_obj = CourseProgress.objects.get(user=user, course=obj)
            return progress_obj.progress
        except CourseProgress.DoesNotExist:
            return 0.0

    def get_number_of_modules(self, obj):
        return obj.modules.count()

    def get_number_of_chapters(self, obj):
        return obj.total_chapters

    def get_chapters_completed(self, obj):
        user = self.context['request'].user
        try:
            progress = CourseProgress.objects.get(user=user, course=obj)
            return len(progress.completed_chapters)
        except CourseProgress.DoesNotExist:
            return 0

    def get_updated_at(self, obj):
        user = self.context['request'].user
        try:
            progress_obj = CourseProgress.objects.get(user=user, course=obj)
            return progress_obj.updated_at
        except CourseProgress.DoesNotExist:
            return None

class QuizAttemptSerializer(serializers.ModelSerializer):
    selected_option = serializers.IntegerField()

    class Meta:
        model = QuizAttempt
        fields = ['selected_option']

    def validate_selected_option(self, value):
        if value not in [1, 2, 3, 4]:
            raise serializers.ValidationError("Selected option must be 1, 2, 3, or 4")
        return value

class MockTestQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockTestQuiz
        fields = ['id', 'question', 'option_1', 'option_2', 'option_3', 'option_4', 'correct_option']

class MockTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockTest
        fields = ['id', 'heading', 'description', 'image', 'created_at', 'duration']

class MockTestAttemptSerializer(serializers.ModelSerializer):
    mock_test = MockTestSerializer(read_only=True)
    results = serializers.SerializerMethodField()

    class Meta:
        model = MockTestAttempt
        fields = ['mock_test', 'score', 'total_questions', 'start_time', 'end_time', 'created_at', 'results']

    def get_results(self, obj):
        results = []
        quizzes = MockTestQuiz.objects.filter(mock_test=obj.mock_test)
        for quiz in quizzes:
            answer = next((a for a in obj.answers if a['quiz_id'] == quiz.id), None)
            if answer:
                results.append({
                    'quiz_id': quiz.id,
                    'question': quiz.question,
                    'selected_option': answer['selected_option'],
                    'selected_option_text': getattr(quiz, f'option_{answer["selected_option"]}'),
                    'correct_option': quiz.correct_option,
                    'correct_option_text': getattr(quiz, f'option_{quiz.correct_option}'),
                    'is_correct': answer['selected_option'] == quiz.correct_option
                })
        return results

class VideoAccessSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    duration_hours = serializers.SerializerMethodField()
    chapter_name = serializers.CharField()
    chapter_description = serializers.CharField(allow_null=True)

    class Meta:
        model = Chapter
        fields = ['id', 'chapter_name', 'chapter_description', 'video_url', 'duration_minutes', 'duration_hours']

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video and hasattr(obj.video, 'url'):
            return request.build_absolute_uri(obj.video.url) if request else None
        return None

    def get_duration_minutes(self, obj):
        if obj.video and obj.video.path and os.path.exists(obj.video.path):
            return round(get_video_duration1(obj.video.path), 2)
        return 0

    def get_duration_hours(self, obj):
        minutes = self.get_duration_minutes(obj)
        return round(minutes / 60, 2)

class StudentDetailSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email')
    date_joined = serializers.DateTimeField(source='created_at')
    profile_picture = serializers.SerializerMethodField()
    purchased_courses = PurchasedCourseSerializer(many=True, source='user.purchased_courses')

    class Meta:
        model = Student
        fields = [
            'full_name', 'email', 'phone_number', 'is_phone_verified', 'dob', 'institution',
            'location', 'role', 'start_date', 'end_date', 'profile_picture', 'date_joined',
            'purchased_courses'
        ]

    def get_profile_picture(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and hasattr(obj.profile_picture, 'url'):
            return request.build_absolute_uri(obj.profile_picture.url) if request else None
        return None