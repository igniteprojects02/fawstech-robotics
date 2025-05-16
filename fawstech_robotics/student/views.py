import random
from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone
from django.contrib.auth import get_user_model
import firebase_admin
from firebase_admin import auth, credentials
from firebase_admin.auth import ExpiredIdTokenError, InvalidIdTokenError
from rest_framework import status, generics
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from twilio.rest import Client
from admin_panel.models import Course, User, Quiz,Author
from student.firebase_config import firebase_app
from .models import (
    Cart,
    CartItem,
    EmailOTP,
    LearningPreference,
    NewsletterSubscriber,
    Order,
    QuizAttempt,
    OrderItem,
    Payment,
    PurchasedCourse,
    Student,
    User as LocalUser,
    CourseProgress,
    MockTestAttempt
)
from .serializers import (
    ChangePasswordSerializer,
    CourseDetailSerializer,
    CreateOrderSerializer,
    ForgotPasswordOTPVerifySerializer,
    ForgotPasswordSerializer,
    AuthorSerializer,
    LearningPreferenceSerializer,
    NewsletterSubscriberSerializer,
    PaymentVerificationSerializer,
    ProfilePictureSerializer,
    PurchasedCourseSerializer,
    ResetPasswordSerializer,
    StudentCourseListSerializer,
    StudentLoginSerializer,
    StudentProfileSerializer,
    StudentSignupSerializer,
    CartSerializer,
    QuizAttemptSerializer,
    CourseWithProgressSerializer,
    CourseProgressSerializer,
    MockTestAttemptSerializer,
    VideoAccessSerializer,
    StudentDetailSerializer
)
from .utils import send_otp_email
from admin_panel.models import MockTest, MockTestQuiz, Chapter
from django.core.exceptions import ObjectDoesNotExist
import razorpay
from razorpay.errors import SignatureVerificationError
from decimal import Decimal
from dateutil import parser as dateutil_parser
import logging

logger = logging.getLogger(__name__)

class NewsletterSubscribeView(APIView):
    def post(self, request):
        serializer = NewsletterSubscriberSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            if NewsletterSubscriber.objects.filter(email=email).exists():
                return Response({'message': 'Already subscribed.'}, status=status.HTTP_200_OK)
            serializer.save()
            return Response({'message': 'Subscribed successfully.'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class StudentSignupView(APIView):
    def post(self, request):
        serializer = StudentSignupSerializer(data=request.data)
        if serializer.is_valid():
            user, otp = serializer.save()  # Get user and OTP from serializer
            refresh = RefreshToken.for_user(user)

            student = Student.objects.get(user=user)
            # Send OTP email
            send_otp_email(student.user.email, otp)

            return Response({
                "message": "Signup successful, OTP sent to email",
                "user": {
                    "email": user.email,
                    "role": user.role,
                    "full_name": student.full_name,
                    "phone_number": student.phone_number
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StudentLoginView(APIView):
    def post(self, request):
        serializer = StudentLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            student = Student.objects.get(user=user)
            return Response({
                "message": "Login successful",
                "user": {
                    "email": user.email,
                    "role": user.role,
                    "full_name": student.full_name,
                    "phone_number": student.phone_number
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GoogleLoginView(APIView):
    def post(self, request):
        id_token = request.data.get('id_token')
        if not id_token:
            return Response({"error": "ID token is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            decoded_token = auth.verify_id_token(id_token)
            email = decoded_token.get('email')
            full_name = decoded_token.get('name')
            phone = decoded_token.get('phone_number', None)

            if not email:
                return Response({"error": "Email not found in token"}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(email=email, defaults={
                'role': 'STUDENT',
                'password': User.objects.make_random_password()
            })

            if created:
                Student.objects.create(
                    user=user,
                    full_name=full_name,
                )

            student = Student.objects.get(user=user)
            if phone and not hasattr(student, 'phone_number'):
                student.phone_number = phone
                student.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful",
                "user": {
                    "email": user.email,
                    "full_name": student.full_name,
                    "phone_number": getattr(student, 'phone_number', None)
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)

        except (InvalidIdTokenError, ExpiredIdTokenError):
            return Response({"error": "Invalid or expired ID token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class SendEmailOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response({"error": "Email is required"}, status=400)

        user, created = User.objects.get_or_create(email=email)

        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp = otp_obj.generate_otp()
        otp_obj.otp = otp
        otp_obj.created_at = timezone.now()
        otp_obj.is_verified = False
        otp_obj.save()

        send_otp_email(email, otp)

        return Response({"message": "OTP sent to email"}, status=status.HTTP_200_OK)
    
class VerifyEmailOTPView(APIView):
    def post(self, request):
        email = request.data.get("email")
        otp = request.data.get("otp")

        if not email or not otp:
            return Response({"error": "Email and OTP are required"}, status=400)

        try:
            user = User.objects.get(email=email)
            otp_obj = EmailOTP.objects.get(user=user)
        except (User.DoesNotExist, EmailOTP.DoesNotExist):
            return Response({"error": "Invalid email or OTP"}, status=400)

        if otp_obj.is_expired():
            return Response({"error": "OTP has expired"}, status=400)

        if otp_obj.otp != otp:
            return Response({"error": "Invalid OTP"}, status=400)

        otp_obj.is_verified = True
        otp_obj.save()

        return Response({"message": "Email verified successfully"}, status=200)
    
class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                
                otp = str(random.randint(100000, 999999))
                otp_instance, created = EmailOTP.objects.get_or_create(user=user)
                otp_instance.otp = otp
                otp_instance.created_at = timezone.now()
                otp_instance.is_verified = False
                otp_instance.save()

                subject = "Your OTP for Password Reset"
                message = f"Your OTP for resetting your password is {otp}."
                email_message = EmailMessage(subject, message, to=[email])
                email_message.send()

                return Response({"message": "OTP sent successfully to your email."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyForgotPasswordOTPView(APIView):
    def post(self, request):
        serializer = ForgotPasswordOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(email=email)
                otp_obj = EmailOTP.objects.get(user=user)

                if otp_obj.is_verified:
                    return Response({"error": "OTP already used."}, status=status.HTTP_400_BAD_REQUEST)

                if otp_obj.otp != otp:
                    return Response({"error": "Invalid OTP."}, status=status.HTTP_400_BAD_REQUEST)

                time_diff = (timezone.now() - otp_obj.created_at).total_seconds()
                if time_diff > 300:
                    return Response({"error": "OTP has expired."}, status=status.HTTP_400_BAD_REQUEST)

                otp_obj.is_verified = True
                otp_obj.save()
                return Response({"message": "OTP verified successfully."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "User does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            except EmailOTP.DoesNotExist:
                return Response({"error": "No OTP found for this user."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(email=email)
                otp_obj = EmailOTP.objects.get(user=user)

                if not otp_obj.is_verified:
                    return Response({"error": "OTP not verified."}, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)
                user.save()

                otp_obj.is_verified = False
                otp_obj.save()

                return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"error": "User not found."}, status=status.HTTP_400_BAD_REQUEST)
            except EmailOTP.DoesNotExist:
                return Response({"error": "OTP not found."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LearningPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Ensure the user is a student
        if request.user.role != 'STUDENT':
            return Response({"error": "Only students can set learning preferences."}, status=status.HTTP_403_FORBIDDEN)

        learning_preference = None  # <-- Initialize to None

        # Check if learning preference already exists
        try:
            learning_preference = LearningPreference.objects.get(user=request.user)
            # If exists, update it
            serializer = LearningPreferenceSerializer(learning_preference, data=request.data, partial=True)
        except LearningPreference.DoesNotExist:
            # If not exists, create new
            serializer = LearningPreferenceSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({
                "message": "Learning preferences saved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK if learning_preference else status.HTTP_201_CREATED)
            # Note: status codes swapped for logic (200 if updating, 201 if creating)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = Student.objects.get(user=request.user)
        serializer = StudentProfileSerializer(student, context={'request': request})
        return Response(serializer.data)

    def patch(self, request):
        student = Student.objects.get(user=request.user)
        serializer = StudentProfileSerializer(student, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully",
                "data": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProfilePictureUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        student = Student.objects.get(user=request.user)
        serializer = ProfilePictureSerializer(student, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile picture updated successfully",
                "data": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

OTP_STORAGE = {}

class SendPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone_number = request.user.student_profile.phone_number
        otp = random.randint(100000, 999999)
        OTP_STORAGE[request.user.id] = str(otp)

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your verification code is {otp}",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )

        return Response({"message": "OTP sent successfully."})
    
class VerifyPhoneOTPView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_id = request.user.id
        entered_otp = request.data.get("otp")

        if not entered_otp:
            return Response({"error": "OTP is required"}, status=400)

        if OTP_STORAGE.get(user_id) == entered_otp:
            student = request.user.student_profile
            student.is_phone_verified = True
            student.save()
            OTP_STORAGE.pop(user_id)
            return Response({"message": "Phone number verified successfully."})
        return Response({"error": "Invalid OTP"}, status=400)

User = get_user_model()

class DeleteStudentProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user

        try:
            if user.role != "STUDENT":
                return Response({"detail": "Only students can delete their profile."}, status=status.HTTP_403_FORBIDDEN)

            user.delete()

            return Response({"detail": "Profile deleted successfully."}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": "Error deleting profile.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class StudentCourseListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        courses = Course.objects.all()
        serializer = StudentCourseListSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)
    
class RecommendedCoursesAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        courses = Course.objects.filter(recommended__in=[True]).order_by('position')
        serializer = StudentCourseListSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)
    
class CourseDetailView(RetrieveAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request 
        return context

class AddToCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        course_id = request.data.get("course_id")

        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=404)

        if PurchasedCourse.objects.filter(user=user, course=course).exists():
            return Response({"error": "You have already purchased this course."}, status=400)

        cart, _ = Cart.objects.get_or_create(user=user)
        if CartItem.objects.filter(cart=cart, course=course).exists():
            return Response({"message": "Already in cart"}, status=200)

        CartItem.objects.create(cart=cart, course=course)
        return Response({"message": "Added to cart"}, status=201)

class RemoveFromCartAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, course_id):
        user = request.user
        try:
            cart = user.cart
            item = cart.items.get(course_id=course_id)
            item.delete()
            return Response({"message": "Removed from cart"}, status=200)
        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            return Response({"error": "Item not found in cart"}, status=404)

class CartDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET))

class CreateRazorpayOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CreateOrderSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        direct_buy = serializer.validated_data["direct_buy"]
        course_ids = serializer.validated_data.get("course_ids", [])

        total_amount = 0
        courses_to_purchase = []

        # Determine courses based on direct buy or cart with filtering
        if direct_buy:
            courses = Course.objects.filter(id__in=course_ids)
        else:
            cart = user.cart
            # Filter cart items to include only the specified course_ids
            cart_items = cart.items.filter(course__id__in=course_ids)
            if not cart_items.exists():
                return Response({"error": "No matching courses found in cart"}, status=400)
            courses = [item.course for item in cart_items]

        # Filter out already purchased courses
        courses = [course for course in courses if not PurchasedCourse.objects.filter(user=user, course=course).exists()]

        if not courses:
            return Response({"message": "All selected courses are already purchased."}, status=400)

        # Handle free and paid courses
        for course in courses:
            # Convert price to Decimal if necessary
            try:
                price = course.offer_price.to_decimal() if hasattr(course.offer_price, "to_decimal") else Decimal(str(course.offer_price))
            except Exception as e:
                return Response({"error": f"Invalid price for course {course.id}"}, status=400)

            if price == 0:
                # Free course: Add to purchased courses and remove from cart
                PurchasedCourse.objects.get_or_create(user=user, course=course)
                if not direct_buy:
                    CartItem.objects.filter(cart=user.cart, course=course).delete()
            else:
                # Paid course: Add to total amount and list of courses to purchase
                amount_to_add = int(price * 100)  # Convert to paisa for Razorpay
                total_amount += amount_to_add
                courses_to_purchase.append(course)

        # If all were free
        if total_amount == 0:
            return Response({"message": "Free courses added to library"}, status=200)

        # Create Razorpay order
        razorpay_order = razorpay_client.order.create(dict(
            amount=total_amount,
            currency="INR",
            payment_capture=1
        ))

        # Create Order in database
        order = Order.objects.create(
            user=user,
            razorpay_order_id=razorpay_order['id'],
            amount=total_amount,
            direct_buy=direct_buy
        )

        # Create OrderItems for paid courses only
        for course in courses_to_purchase:
            OrderItem.objects.create(order=order, course=course)

        return Response({
            "order_id": razorpay_order["id"],
            "amount": total_amount,
            "currency": "INR",
            "message": "Razorpay order created"
        }, status=201)

class VerifyRazorpayPaymentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order_id = serializer.validated_data["order_id"]
        payment_id = serializer.validated_data["payment_id"]
        signature = serializer.validated_data["signature"]

        try:
            razorpay_client.utility.verify_payment_signature({
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })
        except SignatureVerificationError:
            return Response({"error": "Signature verification failed"}, status=400)

        try:
            order = Order.objects.get(razorpay_order_id=order_id)
            if order.is_paid:
                return Response({"error": "Invalid or already paid order"}, status=400)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=400)

        order.razorpay_payment_id = payment_id
        order.razorpay_signature = signature
        order.is_paid = True
        order.save()

        Payment.objects.create(
            order=order,
            razorpay_payment_id=payment_id,
            razorpay_signature=signature,
        )

        for item in order.items.all():
            PurchasedCourse.objects.get_or_create(user=request.user, course=item.course)

        if not order.direct_buy:
            CartItem.objects.filter(cart=request.user.cart, course__in=[item.course for item in order.items.all()]).delete()

        return Response({"message": "Payment verified and courses purchased"}, status=200)

class PurchasedCoursesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        purchased_courses = PurchasedCourse.objects.filter(user=request.user)
        serializer = PurchasedCourseSerializer(
            purchased_courses, many=True, context={'request': request}
        )
        return Response(serializer.data)

class CourseProgressListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CourseWithProgressSerializer

    def get_queryset(self):
        user = self.request.user
        purchased_courses = PurchasedCourse.objects.filter(user=user).values_list('course', flat=True)
        courses = Course.objects.filter(id__in=purchased_courses)
        return courses

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        in_progress = []
        not_started = []
        completed = []

        for course in queryset:
            try:
                progress = CourseProgress.objects.get(user=request.user, course=course)
                serialized = CourseWithProgressSerializer(course, context={'request': request}).data
                if progress.progress >= 99.99:
                    completed.append(serialized)
                elif progress.progress > 0:
                    in_progress.append(serialized)
                else:
                    not_started.append(serialized)
            except CourseProgress.DoesNotExist:
                serialized = CourseWithProgressSerializer(course, context={'request': request}).data
                not_started.append(serialized)

        return Response({
            'in_progress': in_progress,
            'not_started': not_started,
            'completed': completed
        })

class CourseProgressUpdateView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CourseProgressSerializer

    def post(self, request, course_id, *args, **kwargs):
        user = request.user
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'error': 'Course not found'}, status=status.HTTP_404_NOT_FOUND)

        if not PurchasedCourse.objects.filter(user=user, course=course).exists():
            return Response({'error': 'Course not purchased'}, status=status.HTTP_403_FORBIDDEN)

        chapter_id = request.data.get('chapter_id')
        quiz_id = request.data.get('quiz_id')
        completed = request.data.get('completed', True)

        progress, created = CourseProgress.objects.get_or_create(
            user=user, course=course, defaults={'progress': 0.0, 'completed_chapters': [], 'completed_quizzes': []}
        )

        if chapter_id:
            try:
                chapter = Chapter.objects.get(id=chapter_id, module__course=course)
            except Chapter.DoesNotExist:
                return Response({'error': 'Chapter not found or does not belong to course'}, status=status.HTTP_404_NOT_FOUND)
            completed_chapters = progress.completed_chapters
            if completed and chapter.id not in completed_chapters:
                completed_chapters.append(chapter.id)
            elif not completed and chapter.id in completed_chapters:
                completed_chapters.remove(chapter.id)
            progress.completed_chapters = completed_chapters

        if quiz_id:
            try:
                quiz = Quiz.objects.get(id=quiz_id, chapter__module__course=course)
            except Quiz.DoesNotExist:
                return Response({'error': 'Quiz not found or does not belong to course'}, status=status.HTTP_404_NOT_FOUND)
            completed_quizzes = progress.completed_quizzes
            if completed and quiz.id not in completed_quizzes:
                completed_quizzes.append(quiz.id)
            elif not completed and quiz.id in completed_quizzes:
                completed_quizzes.remove(quiz.id)
            progress.completed_quizzes = completed_quizzes

        progress.save()

        return Response({
            'course_id': course.id,
            'progress': progress.progress,
            'completed_chapters': progress.completed_chapters,
            'completed_quizzes': progress.completed_quizzes
        }, status=status.HTTP_200_OK)
    
class QuizAttemptView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizAttemptSerializer

    def post(self, request, quiz_id, *args, **kwargs):
        user = request.user
        try:
            quiz = Quiz.objects.get(id=quiz_id)
        except Quiz.DoesNotExist:
            return Response({'error': 'Quiz not found'}, status=status.HTTP_404_NOT_FOUND)

        course = quiz.chapter.module.course
        if not PurchasedCourse.objects.filter(user=user, course=course).exists():
            return Response({'error': 'Course not purchased'}, status=status.HTTP_403_FORBIDDEN)

        if QuizAttempt.objects.filter(user=user, quiz=quiz).exists():
            return Response({'error': 'Quiz already attempted'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        selected_option = serializer.validated_data['selected_option']
        is_correct = selected_option == quiz.correct_option
        score = 1 if is_correct else 0

        QuizAttempt.objects.create(
            user=user,
            quiz=quiz,
            selected_option=selected_option,
            is_correct=is_correct
        )

        correct_option_text = getattr(quiz, f'option_{quiz.correct_option}')
        return Response({
            'quiz_id': quiz.id,
            'is_correct': is_correct,
            'score': score,
            'correct_option': quiz.correct_option,
            'correct_option_text': correct_option_text
        }, status=status.HTTP_200_OK)
    
class RecentlyAccessedCoursesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CourseWithProgressSerializer

    def get_queryset(self):
        user = self.request.user
        purchased_course_ids = PurchasedCourse.objects.filter(user=user).values_list('course__id', flat=True)
        progress_qs = CourseProgress.objects.filter(
            user=user,
            course__id__in=purchased_course_ids,
            progress__gt=0,
            progress__lt=99.99
        ).order_by('updated_at')
        course_ids = progress_qs.values_list('course__id', flat=True)
        return Course.objects.filter(id__in=course_ids).order_by('id')
    
class MockTestAttemptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, mock_test_id):
        try:
            mock_test = MockTest.objects.get(id=mock_test_id)
        except MockTest.DoesNotExist:
            return Response({"error": "Mock test not found"}, status=status.HTTP_404_NOT_FOUND)

        if MockTestAttempt.objects.filter(user=request.user, mock_test=mock_test).exists():
            return Response({"error": "Mock test already attempted"}, status=status.HTTP_400_BAD_REQUEST)

        answers = request.data.get('answers', [])
        if not isinstance(answers, list):
            return Response({"error": "Answers must be a list"}, status=status.HTTP_400_BAD_REQUEST)

        quizzes = MockTestQuiz.objects.filter(mock_test=mock_test)
        if not quizzes:
            return Response({"error": "No questions in this mock test"}, status=status.HTTP_400_BAD_REQUEST)

        quiz_ids = set(q.id for q in quizzes)
        submitted_quiz_ids = set(a.get('quiz_id') for a in answers if isinstance(a, dict))
        if submitted_quiz_ids != quiz_ids:
            return Response({"error": "Must answer all questions"}, status=status.HTTP_400_BAD_REQUEST)

        for answer in answers:
            if not isinstance(answer, dict) or 'quiz_id' not in answer or 'selected_option' not in answer:
                return Response({"error": "Each answer must have quiz_id and selected_option"}, status=status.HTTP_400_BAD_REQUEST)
            if not isinstance(answer['selected_option'], int) or not 1 <= answer['selected_option'] <= 4:
                return Response({"error": "Selected option must be 1, 2, 3, or 4"}, status=status.HTTP_400_BAD_REQUEST)
            if answer['quiz_id'] not in quiz_ids:
                return Response({"error": f"Invalid quiz_id: {answer['quiz_id']}"}, status=status.HTTP_400_BAD_REQUEST)

        start_time = request.data.get('start_time')
        if not start_time:
            return Response({"error": "Start time required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            logger.debug(f"Parsing start_time: {start_time}")
            start_time = dateutil_parser.isoparse(start_time)
            if not start_time.tzinfo:
                start_time = start_time.replace(tzinfo=timezone.utc)
        except ValueError as e:
            logger.error(f"Invalid start_time format: {start_time}, error: {str(e)}")
            return Response({"error": f"Invalid start_time format: {start_time}"}, status=status.HTTP_400_BAD_REQUEST)

        end_time = timezone.now()
        if mock_test.duration:
            duration_minutes = (end_time - start_time).total_seconds() / 60
            if duration_minutes > mock_test.duration:
                return Response({"error": "Time limit exceeded"}, status=status.HTTP_400_BAD_REQUEST)

        score = 0
        for answer in answers:
            quiz = next(q for q in quizzes if q.id == answer['quiz_id'])
            if answer['selected_option'] == quiz.correct_option:
                score += 1

        attempt = MockTestAttempt(
            user=request.user,
            mock_test=mock_test,
            answers=answers,
            score=score,
            total_questions=len(quizzes),
            start_time=start_time,
            end_time=end_time
        )
        attempt.save()

        serializer = MockTestAttemptSerializer(attempt)
        return Response(serializer.data, status=status.HTTP_200_OK)

class MockTestResultsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MockTestAttemptSerializer

    def get_queryset(self):
        return MockTestAttempt.objects.filter(user=self.request.user).order_by('-created_at')

class VideoAccessView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id, chapter_id):
        if request.user.role != 'STUDENT':
            return Response({"error": "Only students can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)

        try:
            course = Course.objects.get(id=course_id)
        except ObjectDoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        if not PurchasedCourse.objects.filter(user=request.user, course=course).exists():
            return Response({"error": "Course not purchased"}, status=status.HTTP_403_FORBIDDEN)

        try:
            chapter = Chapter.objects.get(id=chapter_id, module__course=course)
        except ObjectDoesNotExist:
            return Response({"error": "Chapter not found or does not belong to this course"}, status=status.HTTP_404_NOT_FOUND)

        serializer = VideoAccessSerializer(chapter, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class StudentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        if request.user.role != 'ADMIN':
            return Response({"error": "Only admins can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)

        try:
            student = Student.objects.get(user__id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = StudentDetailSerializer(student, context={'request': request})
        return Response({
            "message": "Student details retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    
class AuthorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id):
        if request.user.role != 'STUDENT':
            return Response({"error": "Only students can access this endpoint"}, status=status.HTTP_403_FORBIDDEN)

        try:
            author = Author.objects.get(id=author_id)
        except Author.DoesNotExist:
            return Response({"error": "Author not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = AuthorSerializer(author, context={'request': request})
        return Response({
            "message": "Author details retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)