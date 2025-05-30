from django.urls import path
from .views import( StudentSignupView,StudentLoginView,GoogleLoginView,SendEmailOTPView,VerifyEmailOTPView,
                   ForgotPasswordView,VerifyForgotPasswordOTPView,ResetPasswordView,LearningPreferenceView,
                   NewsletterSubscribeView,StudentProfileView, ProfilePictureUpdateView,ChangePasswordView, SendPhoneOTPView,
                   VerifyPhoneOTPView,DeleteStudentProfileView,StudentCourseListView,RecommendedCoursesAPIView,CourseDetailView,
                   AddToCartAPIView,RemoveFromCartAPIView,CartDetailAPIView,CreateRazorpayOrderAPIView,VerifyRazorpayPaymentAPIView,
                   PurchasedCoursesAPIView,CourseProgressListView,CourseProgressUpdateView,QuizAttemptView,RecentlyAccessedCoursesView,
                   MockTestAttemptView,MockTestResultsView,VideoAccessView,AuthorDetailView)
urlpatterns = [
    path('subscribe-newsletter/', NewsletterSubscribeView.as_view(), name='subscribe-newsletter'),
    path('signup/', StudentSignupView.as_view(), name='student_signup'),
    path('login/', StudentLoginView.as_view(), name='student-login'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path("send-email-otp/", SendEmailOTPView.as_view(), name='send-email-otp'),
    path("verify-email-otp/", VerifyEmailOTPView.as_view(),name='verify-email-otp'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('verify-forgot-password-otp/', VerifyForgotPasswordOTPView.as_view(), name='verify-forgot-password-otp'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('learning-preferences/', LearningPreferenceView.as_view()),  
    path('learning-preferences/<int:student_id>/', LearningPreferenceView.as_view()),
    path('profile/', StudentProfileView.as_view(), name='student-profile'),
    path('profile-picture/', ProfilePictureUpdateView.as_view(), name='profile-picture-update'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('send-otp/', SendPhoneOTPView.as_view(),name='send otp'),
    path('verify-otp/', VerifyPhoneOTPView.as_view(),name='verify otp'),
    path('delete-profile/', DeleteStudentProfileView.as_view(), name='delete-student-profile'),
    path('courses/', StudentCourseListView.as_view(), name='student-courses'),
    path('recommended-courses/', RecommendedCoursesAPIView.as_view(), name='recommended-courses'),
    path('course/<int:id>/', CourseDetailView.as_view(), name='course-detail'),
    path("cart/add/", AddToCartAPIView.as_view(), name="add-to-cart"),
    path("cart/remove/<str:course_id>/", RemoveFromCartAPIView.as_view(), name="remove-from-cart"),
    path("cart/", CartDetailAPIView.as_view(), name="view-cart"),
    path("checkout/create-order/", CreateRazorpayOrderAPIView.as_view(), name="create-razorpay-order"),
    path("checkout/verify-payment/", VerifyRazorpayPaymentAPIView.as_view(), name="verify-razorpay-payment"),
    path("courses/purchased/", PurchasedCoursesAPIView.as_view(), name="purchased-courses"),
    path('courses/progress/', CourseProgressListView.as_view(), name='course-progress-list'),
    path('courses/<int:course_id>/progress/', CourseProgressUpdateView.as_view(), name='course-progress-update'),
    path('quizzes/<int:quiz_id>/attempt/', QuizAttemptView.as_view(), name='quiz-attempt'),
    path('courses/recently-accessed/', RecentlyAccessedCoursesView.as_view(), name='recently-accessed-courses'),
    path('mock-tests/<int:mock_test_id>/attempt/', MockTestAttemptView.as_view(), name='mock-test-attempt'),
    path('mock-tests/results/', MockTestResultsView.as_view(), name='mock-test-results'),
    path('courses/<int:course_id>/chapters/<int:chapter_id>/video/', VideoAccessView.as_view(), name='video-access'),
    path('author/<int:author_id>/',AuthorDetailView.as_view(), name='author-detail'),

]
