"""
A mock version of the v1 API, providing dummy data for partner integration
testing.
"""

from django.core.exceptions import PermissionDenied
from django.http import Http404
from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_207_MULTI_STATUS,
    HTTP_413_REQUEST_ENTITY_TOO_LARGE,
    HTTP_422_UNPROCESSABLE_ENTITY
)

from registrar.apps.api.serializers import (
    CourseRunSerializer,
    ProgramSerializer,
    RequestedLearnerProgramEnrollmentSerializer,
)
from registrar.apps.api.v0.data import (
    FAKE_ORG_DICT,
    FAKE_ORG_PROGRAMS,
    FAKE_PROGRAM_DICT,
    FAKE_PROGRAM_COURSE_RUNS,
)


class MockProgramListView(ListAPIView):
    """
    A view for listing program objects.

    Path: /api/v0/programs?org={org_key}

    All programs within organization specified by `org_key` are returned.
    For users with global organization access, `org_key` can be omitted in order
    to return all programs.

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access to specified organization.
     * 404: Organization does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProgramSerializer

    def get_queryset(self):
        org_key = self.request.GET.get('org', None)
        if not org_key:
            raise PermissionDenied()
        org = FAKE_ORG_DICT.get(org_key)
        if not org:
            raise Http404()
        if not org.metadata_readable:
            raise PermissionDenied()
        return FAKE_ORG_PROGRAMS[org.key]


class MockProgramSpecificViewMixin(object):
    """
    A mixin for views that operate on or within a specific program.
    """

    @property
    def program(self):
        """
        The program specified by the `program_key` URL parameter.
        """
        program_key = self.kwargs['program_key']
        if program_key not in FAKE_PROGRAM_DICT:
            raise Http404()
        return FAKE_PROGRAM_DICT[program_key]


class MockProgramRetrieveView(MockProgramSpecificViewMixin, RetrieveAPIView):
    """
    A view for retrieving a single program object.

    Path: /api/v0/programs/{program_key}

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = ProgramSerializer

    def get_object(self):
        if self.program.managing_organization.metadata_readable:
            return self.program
        else:
            raise PermissionDenied()


class MockProgramCourseListView(MockProgramSpecificViewMixin, ListAPIView):
    """
    A view for listing courses in a program.

    Path: /api/v0/programs/{program_key}/courses

    Returns:
     * 200: OK
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
    """

    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = CourseRunSerializer

    def get_queryset(self):
        if self.program.managing_organization.metadata_readable:
            return FAKE_PROGRAM_COURSE_RUNS[self.program.key]
        else:
            raise PermissionDenied()


class MockProgramEnrollmentView(CreateAPIView, MockProgramSpecificViewMixin):
    """
    A view for enrolling students in a program.

    Path: /api/v1/programs/{program_key}/enrollments

    Returns:
     * 200: Returns a map of students and their enrollment status.
     * 207: Not all students enrolled. Returns resulting enrollment status.
     * 401: User is not authenticated
     * 403: User lacks read access organization of specified program.
     * 404: Program does not exist.
     * 413: Payload too large, over 25 students supplied.
     * 422: Invalid request, unable to enroll students.
    """
    authentication_classes = (JwtAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    serializer_class = RequestedLearnerProgramEnrollmentSerializer

    def post(self, request, *args, **kwargs):
        """ Enroll up to 25 students in program """
        if not self.program.managing_organization.metadata_readable:
            raise PermissionDenied()

        response = {}
        error_status = None

        if not isinstance(request.data, list):
            raise ValidationError()

        if len(request.data) > 25:
            return Response(
                'enrollement limit 25', HTTP_413_REQUEST_ENTITY_TOO_LARGE
            )

        for enrollee in request.data:
            enrollee_serializer = RequestedLearnerProgramEnrollmentSerializer(
                data=enrollee
            )

            if enrollee_serializer.is_valid():
                enrollee = enrollee_serializer.data
                student_key = enrollee['student_key']
                if student_key in response:
                    response[student_key] = 'duplicated'
                    error_status = HTTP_207_MULTI_STATUS
                else:
                    response[student_key] = enrollee['status']
            else:
                try:
                    if 'status' in enrollee_serializer.errors:
                        response[enrollee['student_key']] = 'invalid-status'
                    else:
                        response[enrollee['student_key']] = 'internal-error'
                    error_status = HTTP_207_MULTI_STATUS
                except KeyError:
                    return Response(
                        'student_key required', HTTP_422_UNPROCESSABLE_ENTITY
                    )

        return Response(response, error_status)
