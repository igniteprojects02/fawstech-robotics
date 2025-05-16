from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import ListAPIView
from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import permissions
from rest_framework_simplejwt.tokens import RefreshToken
from student.models import Student
from .models import Course, Author
from .utils import get_video_duration
from .models import (
    User,
    LandingMedia,
    GalleryImage,
    Course,
    Module,
    Chapter,
    Quiz,
    MockTest,
    MockTestQuiz,
    Event,
    Author,
)
from .serializers import (
    LandingMediaSerializer,
    GalleryImageSerializer,
    CourseSerializer,
    ModuleSerializer,
    ChapterSerializer,
    QuizSerializer,
    EventSerializer,
    MockTestSerializer,
    MockTestQuizSerializer,
    AuthorSerializer,
    StudentListSerializer,
    StudentDetailSerializer,
)
import os
import logging

logger = logging.getLogger(__name__)

class AdminLoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"error": "Email and password are required"}, status=400)

        user = authenticate(request, email=email, password=password)
        if user and user.role == "ADMIN":
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            })
        return Response({"error": "Invalid credentials"}, status=400)

class AuthorCreateView(generics.CreateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        logger.debug(f"Request data: {request.data}")
        logger.debug(f"Request files: {request.FILES}")
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Author created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class AuthorListView(generics.ListAPIView):
    queryset = Author.objects.all().order_by('name')
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]

class AuthorDetailView(generics.RetrieveAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class AuthorUpdateView(generics.UpdateAPIView):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def perform_update(self, serializer):
        author = self.get_object()
        new_profile_picture = self.request.FILES.get('profile_picture')
        if new_profile_picture and author.profile_picture:
            if os.path.isfile(author.profile_picture.path):
                os.remove(author.profile_picture.path)
        serializer.save()

    def update(self, request, *args, **kwargs):
        logger.debug(f"Update request data: {request.data}")
        logger.debug(f"Update request files: {request.FILES}")
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Author updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class AuthorByCourseView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
            if not course.author:
                return Response({"message": "No author assigned to this course"}, status=status.HTTP_200_OK)
            serializer = AuthorSerializer(course.author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

class LandingMediaUploadView(generics.CreateAPIView):
    queryset = LandingMedia.objects.all()
    serializer_class = LandingMediaSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Landing media uploaded successfully",
        }, status=status.HTTP_201_CREATED, headers=headers)

class LandingMediaListView(generics.ListAPIView):
    queryset = LandingMedia.objects.all().order_by('-uploaded_at')
    serializer_class = LandingMediaSerializer
    permission_classes = [permissions.AllowAny]

class LandingMediaDeleteView(generics.DestroyAPIView):
    queryset = LandingMedia.objects.all()
    serializer_class = LandingMediaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Landing media deleted successfully"}, status=status.HTTP_200_OK)

class GalleryImageUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('images')
        if not files:
            return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

        images = [GalleryImage(file=file) for file in files]
        GalleryImage.objects.bulk_create(images)
        serializer = GalleryImageSerializer(images, many=True, context={'request': request})
        return Response({
            "message": f"{len(images)} image(s) uploaded successfully",
        }, status=status.HTTP_201_CREATED)

class GalleryImageListView(APIView):
    def get(self, request, *args, **kwargs):
        images = GalleryImage.objects.all().order_by('-uploaded_at')
        serializer = GalleryImageSerializer(images, many=True, context={'request': request})
        return Response(serializer.data)
    
class GalleryImageDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, *args, **kwargs):
        try:
            image = GalleryImage.objects.get(pk=pk)
            image.delete()
            return Response({"message": "Gallery image deleted successfully"}, status=status.HTTP_200_OK)
        except GalleryImage.DoesNotExist:
            return Response({"error": "Image not found"}, status=status.HTTP_404_NOT_FOUND)

class CourseCreateView(generics.CreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Course created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class CourseListView(generics.ListAPIView):
    queryset = Course.objects.prefetch_related('modules__chapters__quizzes', 'author').all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.prefetch_related('modules__chapters__quizzes', 'author')
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response({
            "message": "Course details retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class ModuleCreateView(generics.CreateAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_id')
        course = Course.objects.get(id=course_id)
        serializer.save(course=course)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Module created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class ModuleDetailView(generics.RetrieveAPIView):
    queryset = Module.objects.prefetch_related('chapters__quizzes')
    serializer_class = ModuleSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class ChapterCreateView(generics.CreateAPIView):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def perform_create(self, serializer):
        module_id = self.kwargs.get('module_id')
        module = Module.objects.get(id=module_id)
        serializer.save(module=module)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Chapter created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class ChapterDetailView(generics.RetrieveAPIView):
    queryset = Chapter.objects.prefetch_related('quizzes')
    serializer_class = ChapterSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class QuizCreateView(generics.CreateAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        chapter_id = self.kwargs.get('chapter_id')
        chapter = Chapter.objects.get(id=chapter_id)
        serializer.save(chapter=chapter)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Quiz created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class QuizDetailView(generics.RetrieveAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

class RecommendedCoursesView(generics.ListAPIView):
    queryset = Course.objects.filter(recommended__in=[True]).order_by('position')
    serializer_class = CourseSerializer
    permission_classes = [permissions.AllowAny]

class RecommendCourseView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        recommended = request.data.get('recommended')
        position = request.data.get('position')

        if recommended not in [True, False, "true", "false", "True", "False"]:
            return Response({"error": "Invalid value for recommended"}, status=400)

        course.recommended = str(recommended).lower() == "true"

        if course.recommended:
            if position is not None:
                course.position = position
            else:
                return Response({"error": "Position is required when recommending a course"}, status=400)
        else:
            course.position = None

        course.save()
        serializer = CourseSerializer(course)
        return Response({
            "message": "Course recommendation updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class CourseUpdateView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def perform_update(self, serializer):
        course = self.get_object()
        new_thumbnail = self.request.FILES.get('thumbnail')
        if new_thumbnail and course.thumbnail:
            if os.path.isfile(course.thumbnail.path):
                os.remove(course.thumbnail.path)
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Course updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class ModuleDeleteView(generics.DestroyAPIView):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Module deleted successfully"}, status=status.HTTP_200_OK)

class ChapterUpdateView(generics.UpdateAPIView):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    lookup_field = 'id'

    def perform_update(self, serializer):
        chapter = self.get_object()
        new_video = self.request.FILES.get('video')
        if new_video and chapter.video:
            if os.path.isfile(chapter.video.path):
                os.remove(chapter.video.path)
        serializer.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Chapter updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class ChapterDeleteView(generics.DestroyAPIView):
    queryset = Chapter.objects.all()
    serializer_class = ChapterSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Chapter deleted successfully"}, status=status.HTTP_200_OK)

class QuizUpdateView(generics.UpdateAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            "message": "Quiz updated successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class QuizDeleteView(generics.DestroyAPIView):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Quiz deleted successfully"}, status=status.HTTP_200_OK)

class CourseDeleteView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Course deleted successfully"}, status=status.HTTP_200_OK)

class CourseSearchView(ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        query = self.request.query_params.get('query', '')
        if query:
            return Course.objects.select_related('author').filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__icontains=query) |
                Q(price_inr__icontains=query) |
                Q(offer_price__icontains=query) |
                Q(author__name__icontains=query)
            )
        return Course.objects.none()

class EventCreateView(generics.CreateAPIView):
    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Event created successfully",
        }, status=status.HTTP_201_CREATED, headers=headers)

class EventListView(generics.ListAPIView):
    queryset = Event.objects.all().order_by('event_date')
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

class EventDeleteView(generics.DestroyAPIView):
    queryset = Event.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Event deleted successfully"}, status=status.HTTP_200_OK)

class MockTestCreateView(generics.CreateAPIView):
    queryset = MockTest.objects.all()
    serializer_class = MockTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Mock test created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class MockTestListView(generics.ListAPIView):
    queryset = MockTest.objects.all().order_by('-created_at')
    serializer_class = MockTestSerializer
    permission_classes = [permissions.AllowAny]

class MockTestDeleteView(generics.DestroyAPIView):
    queryset = MockTest.objects.all()
    serializer_class = MockTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Mock test deleted successfully"}, status=status.HTTP_200_OK)

class MockTestQuizCreateView(generics.CreateAPIView):
    queryset = MockTestQuiz.objects.all()
    serializer_class = MockTestQuizSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            "message": "Mock test quiz created successfully",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

class MockTestQuizDeleteView(generics.DestroyAPIView):
    queryset = MockTestQuiz.objects.all()
    serializer_class = MockTestQuizSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Mock test quiz deleted successfully"}, status=status.HTTP_200_OK)

class CourseMetaAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id):
        try:
            course = Course.objects.get(id=id)
            modules = course.modules.all()

            module_count = modules.count()
            chapter_count = 0
            total_duration = 0

            for module in modules:
                chapters = module.chapters.all()
                chapter_count += chapters.count()

                for chapter in chapters:
                    if chapter.video and os.path.exists(chapter.video.path):
                        duration = get_video_duration(chapter.video.path)
                        total_duration += duration

            return Response({
                "course_id": str(course.id),
                "course_name": course.name,
                "total_modules": module_count,
                "total_chapters": chapter_count,
                "total_duration_minutes": round(total_duration, 2),
                "total_duration_hours": round(total_duration / 60, 2)
            })

        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=404)

class StudentListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        students = User.objects.filter(role='STUDENT', student_profile__isnull=False)
        
        search_query = request.query_params.get('search', None)
        if search_query:
            students = students.filter(
                student_profile__full_name__icontains=search_query
            ) | students.filter(email__icontains=search_query)
        
        serializer = StudentListSerializer(students, many=True)
        return Response(serializer.data)

class StudentDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, student_id):
        try:
            student = Student.objects.get(user__id=student_id, user__role='STUDENT')
            serializer = StudentDetailSerializer(student)
            return Response(serializer.data)
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND
            )