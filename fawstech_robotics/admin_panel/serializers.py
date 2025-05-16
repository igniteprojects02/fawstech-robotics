from rest_framework import serializers
import json
from .models import LandingMedia, GalleryImage, Course, Module, Chapter, Quiz, Event, MockTestQuiz, MockTest, Author
from student.models import Student, PurchasedCourse
from admin_panel.models import User, Course
from django.conf import settings

class AuthorSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)
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

    def validate_experience_in_years(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Experience in years cannot be negative")
        return value

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

    def to_internal_value(self, data):
        # Create a mutable copy of the data
        mutable_data = data.copy()

        # Helper function to process a field
        def process_field(field_name, field_value):
            if field_value is not None and field_value != '':
                try:
                    # Log the raw input for debugging
                    print(f"Raw {field_name}: {field_value} (type: {type(field_value)})")
                    # Parse the JSON string (removing extra quotes if present)
                    field_value = field_value.strip()
                    if field_value.startswith('"') and field_value.endswith('"'):
                        field_value = field_value[1:-1]
                    parsed_value = json.loads(field_value)
                    print(f"Parsed {field_name}: {parsed_value} (type: {type(parsed_value)})")
                    # Validate the parsed list directly
                    validated_value = self.validate_list_field(parsed_value, field_name.replace('_', ' ').title())
                    # Convert back to JSON string for storage
                    json_value = json.dumps(validated_value)
                    print(f"Final {field_name} (for storage): {json_value} (type: {type(json_value)})")
                    return json_value
                except json.JSONDecodeError as e:
                    raise serializers.ValidationError(f"{field_name.replace('_', ' ').title()} must be a valid JSON list: {str(e)}")
            return None

        # Handle professional_experience
        professional_experience = mutable_data.get('professional_experience')
        if professional_experience:
            mutable_data['professional_experience'] = process_field('professional_experience', professional_experience)

        # Handle education_and_teaching
        education_and_teaching = mutable_data.get('education_and_teaching')
        if education_and_teaching:
            mutable_data['education_and_teaching'] = process_field('education_and_teaching', education_and_teaching)

        # Handle author_and_content_creator
        author_and_content_creator = mutable_data.get('author_and_content_creator')
        if author_and_content_creator:
            mutable_data['author_and_content_creator'] = process_field('author_and_content_creator', author_and_content_creator)

        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if instance.profile_picture and hasattr(instance.profile_picture, 'url'):
            representation['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url) if request else None
        else:
            representation['profile_picture'] = None

        # Handle professional_experience
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

        # Handle education_and_teaching
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

        # Handle author_and_content_creator
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

class LandingMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = LandingMedia
        fields = ['id', 'media_type', 'file', 'uploaded_at']

class GalleryImageSerializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = ['id', 'file', 'uploaded_at']

    def get_file(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

class QuizSerializer(serializers.ModelSerializer):
    chapter = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'chapter', 'question', 'option_1', 'option_2', 'option_3', 'option_4', 'correct_option']

class ChapterSerializer(serializers.ModelSerializer):
    quizzes = QuizSerializer(many=True, read_only=True)
    module = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Chapter
        fields = ['id', 'module', 'chapter_name', 'chapter_description', 'video', 'quizzes']

class ModuleSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)
    course = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Module
        fields = ['id', 'course', 'module_name', 'chapters']

class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    author = AuthorSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=Author.objects.all(), source='author', write_only=True, required=False, allow_null=True
    )
    what_will_you_learn = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    who_is_this_course_for = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    course_requirements = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_course_updated = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = Course
        fields = [
            'id', 'thumbnail', 'name', 'description', 'category', 'author', 'author_id',
            'what_you_will_learn_1', 'what_you_will_learn_2', 'what_you_will_learn_3',
            'what_you_will_learn_4', 'what_you_will_learn_5', 'what_you_will_learn_6',
            'price_inr', 'offer_price', 'recommended', 'position', 'modules', 'total_chapters',
            'total_quizzes', 'why_choose_this_course', 'what_will_you_learn', 'is_course_updated',
            'who_is_this_course_for', 'course_requirements'
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

    def to_internal_value(self, data):
        mutable_data = data.copy()

        def process_field(field_name, field_value):
            if field_value is not None and field_value != '':
                try:
                    field_value = field_value.strip()
                    if field_value.startswith('"') and field_value.endswith('"'):
                        field_value = field_value[1:-1]
                    parsed_value = json.loads(field_value)
                    validated_value = self.validate_list_field(parsed_value, field_name.replace('_', ' ').title())
                    return json.dumps(validated_value)
                except json.JSONDecodeError as e:
                    raise serializers.ValidationError(f"{field_name.replace('_', ' ').title()} must be a valid JSON list: {str(e)}")
            return None

        # Handle what_will_you_learn
        what_will_you_learn = mutable_data.get('what_will_you_learn')
        if what_will_you_learn:
            mutable_data['what_will_you_learn'] = process_field('what_will_you_learn', what_will_you_learn)

        # Handle who_is_this_course_for
        who_is_this_course_for = mutable_data.get('who_is_this_course_for')
        if who_is_this_course_for:
            mutable_data['who_is_this_course_for'] = process_field('who_is_this_course_for', who_is_this_course_for)

        # Handle course_requirements
        course_requirements = mutable_data.get('course_requirements')
        if course_requirements:
            mutable_data['course_requirements'] = process_field('course_requirements', course_requirements)

        return super().to_internal_value(mutable_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Handle what_will_you_learn
        if instance.what_will_you_learn:
            if isinstance(instance.what_will_you_learn, str):
                try:
                    representation['what_will_you_learn'] = json.loads(instance.what_will_you_learn)
                except json.JSONDecodeError:
                    representation['what_will_you_learn'] = None
            elif isinstance(instance.what_will_you_learn, list):
                representation['what_will_you_learn'] = instance.what_will_you_learn
            else:
                representation['what_will_you_learn'] = None
        else:
            representation['what_will_you_learn'] = None

        # Handle who_is_this_course_for
        if instance.who_is_this_course_for:
            if isinstance(instance.who_is_this_course_for, str):
                try:
                    representation['who_is_this_course_for'] = json.loads(instance.who_is_this_course_for)
                except json.JSONDecodeError:
                    representation['who_is_this_course_for'] = None
            elif isinstance(instance.who_is_this_course_for, list):
                representation['who_is_this_course_for'] = instance.who_is_this_course_for
            else:
                representation['who_is_this_course_for'] = None
        else:
            representation['who_is_this_course_for'] = None

        # Handle course_requirements
        if instance.course_requirements:
            if isinstance(instance.course_requirements, str):
                try:
                    representation['course_requirements'] = json.loads(instance.course_requirements)
                except json.JSONDecodeError:
                    representation['course_requirements'] = None
            elif isinstance(instance.course_requirements, list):
                representation['course_requirements'] = instance.course_requirements
            else:
                representation['course_requirements'] = None
        else:
            representation['course_requirements'] = None

        return representation

class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = '__all__'

class MockTestQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockTestQuiz
        fields = '__all__'

class MockTestSerializer(serializers.ModelSerializer):
    quizzes = MockTestQuizSerializer(many=True, read_only=True)

    class Meta:
        model = MockTest
        fields = ['id', 'heading', 'description', 'image', 'created_at', 'quizzes', 'duration']

class StudentListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()
    full_name = serializers.CharField(source='student_profile.full_name')
    profile_picture = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(source='student_profile.created_at')

    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'date_joined', 'profile_picture']

    def get_profile_picture(self, obj):
        if obj.student_profile.profile_picture:
            return f"{settings.MEDIA_URL}{obj.student_profile.profile_picture}"
        return None

class PurchasedCourseSerializer(serializers.ModelSerializer):
    thumbnail = serializers.SerializerMethodField()
    name = serializers.CharField(source='course.name')
    description = serializers.CharField(source='course.description')
    real_price = serializers.DecimalField(source='course.price_inr', max_digits=10, decimal_places=2)
    offer_price = serializers.DecimalField(source='course.offer_price', max_digits=10, decimal_places=2, allow_null=True)
    author = AuthorSerializer(source='course.author', read_only=True)
    purchased_at = serializers.DateTimeField()

    class Meta:
        model = PurchasedCourse
        fields = ['thumbnail', 'name', 'description', 'real_price', 'offer_price', 'author', 'purchased_at']

    def get_thumbnail(self, obj):
        if obj.course.thumbnail:
            return f"{settings.MEDIA_URL}{obj.course.thumbnail}"
        return None

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
        if obj.profile_picture:
            return f"{settings.MEDIA_URL}{obj.profile_picture}"
        return None