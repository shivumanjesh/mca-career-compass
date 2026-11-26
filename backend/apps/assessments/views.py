"""Phase 2 REST API views for categories, dimensions, question bank, templates, and publishing."""
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import HasAnyPermission, HasInstitutionPermission
from apps.assessments.bulk_import import (
    build_question_template_csv,
    build_question_template_xlsx,
    commit_question_import,
    parse_and_validate_question_upload,
)
from apps.assessments.models import (
    AssessmentAssignment,
    AssessmentCategory,
    AssessmentDimension,
    AssessmentTemplate,
    AssessmentVersion,
    Question,
)
from apps.assessments.serializers import (
    AssessmentAssignmentCreateSerializer,
    AssessmentAssignmentSerializer,
    AssessmentAssignmentUpdateSerializer,
    AssessmentCategorySerializer,
    AssessmentCategoryWriteSerializer,
    AssessmentDimensionSerializer,
    AssessmentDimensionWriteSerializer,
    AssessmentTemplateCreateSerializer,
    AssessmentTemplateSerializer,
    AssessmentTemplateUpdateSerializer,
    AssessmentVersionDraftUpdateSerializer,
    AssessmentVersionSerializer,
    QuestionSerializer,
    QuestionWriteSerializer,
)
from apps.assessments.services import (
    clone_version_to_draft,
    create_assessment_template,
    create_category,
    create_dimension,
    create_question,
    publish_assessment_version,
    seed_starter_catalogue,
    update_category,
    update_dimension,
    update_draft_version,
    update_question,
)
from apps.audit.services import log_audit_event
from apps.core.pagination import StandardResultsSetPagination
from apps.tenancy.mixins import require_active_institution


def _paginate(qs, request, serializer_cls):
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(qs, request)
    return paginator.get_paginated_response(serializer_cls(page, many=True).data)


class SeedStarterCatalogueView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.dimension.manage")]

    def post(self, request):
        inst = require_active_institution(request)
        res = seed_starter_catalogue(institution=inst, actor_user=request.user, request=request)
        return Response(res, status=status.HTTP_200_OK)


class CategoryListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.dimension.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            AssessmentCategory.objects.for_institution(inst)
            .annotate(dimension_count=Count("dimensions", distinct=True))
            .order_by("sort_order", "name")
        )
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, AssessmentCategorySerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = AssessmentCategoryWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cat = create_category(
            institution=inst,
            actor_user=request.user,
            request=request,
            name=serializer.validated_data["name"],
            description=serializer.validated_data["description"],
            sort_order=serializer.validated_data["sort_order"],
        )
        return Response(AssessmentCategorySerializer(cat).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.dimension.manage")]

    def patch(self, request, category_id):
        inst = require_active_institution(request)
        cat = get_object_or_404(AssessmentCategory.objects.for_institution(inst), id=category_id)
        serializer = AssessmentCategoryWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_category(category=cat, data=serializer.validated_data, actor_user=request.user, request=request)
        return Response(AssessmentCategorySerializer(updated).data)


class DimensionListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.dimension.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            AssessmentDimension.objects.for_institution(inst)
            .select_related("category")
            .prefetch_related("dimension_tags__skill_tag")
            .order_by("sort_order", "name")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(code__icontains=search) | Q(name__icontains=search))
        category_id = request.query_params.get("category_id", "").strip()
        if category_id:
            qs = qs.filter(category_id=category_id)
        family = request.query_params.get("measurement_family", "").strip()
        if family:
            qs = qs.filter(measurement_family=family)
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, AssessmentDimensionSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = AssessmentDimensionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        dim = create_dimension(
            institution=inst,
            category_id=data["category_id"],
            code=data["code"],
            name=data["name"],
            description=data.get("description", ""),
            measurement_family=data["measurement_family"],
            interpretation_guidance=data.get("interpretation_guidance", ""),
            sort_order=data.get("sort_order", 0),
            skill_tags=data.get("skill_tags"),
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentDimensionSerializer(dim).data, status=status.HTTP_201_CREATED)


class DimensionDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.dimension.manage")]

    def patch(self, request, dimension_id):
        inst = require_active_institution(request)
        dim = get_object_or_404(AssessmentDimension.objects.for_institution(inst), id=dimension_id)
        serializer = AssessmentDimensionWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_dimension(dimension=dim, data=serializer.validated_data, actor_user=request.user, request=request)
        return Response(AssessmentDimensionSerializer(updated).data)


class QuestionListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.question.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            Question.objects.for_institution(inst)
            .select_related("created_by", "rubric")
            .prefetch_related("options", "question_dimensions__dimension")
            .order_by("-created_at", "question_code")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(question_code__icontains=search) | Q(prompt__icontains=search))
        q_type = request.query_params.get("question_type", "").strip()
        if q_type:
            qs = qs.filter(question_type=q_type)
        family = request.query_params.get("measurement_family", "").strip()
        if family:
            qs = qs.filter(measurement_family=family)
        difficulty = request.query_params.get("difficulty", "").strip()
        if difficulty:
            qs = qs.filter(difficulty=difficulty)
        dimension_id = request.query_params.get("dimension_id", "").strip()
        if dimension_id:
            qs = qs.filter(question_dimensions__dimension_id=dimension_id).distinct()
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, QuestionSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = QuestionWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        q = create_question(
            institution=inst,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(QuestionSerializer(q).data, status=status.HTTP_201_CREATED)


class QuestionDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.question.manage")]

    def get(self, request, question_id):
        inst = require_active_institution(request)
        q = get_object_or_404(
            Question.objects.for_institution(inst)
            .select_related("created_by", "rubric")
            .prefetch_related("options", "question_dimensions__dimension"),
            id=question_id,
        )
        return Response(QuestionSerializer(q).data)

    def patch(self, request, question_id):
        inst = require_active_institution(request)
        q = get_object_or_404(Question.objects.for_institution(inst), id=question_id)
        serializer = QuestionWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_question(
            question=q,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(QuestionSerializer(updated).data)


class TemplateListCreateView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [HasAnyPermission("assessment.template.manage", "assessment.assign")]
        return [HasInstitutionPermission("assessment.template.manage")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            AssessmentTemplate.objects.for_institution(inst)
            .prefetch_related("versions__version_questions")
            .order_by("-created_at")
        )
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, AssessmentTemplateSerializer)

    def post(self, request):
        inst = require_active_institution(request)
        serializer = AssessmentTemplateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        template = create_assessment_template(
            institution=inst,
            name=data["name"],
            description=data.get("description", ""),
            duration_minutes=data.get("duration_minutes", 60),
            max_attempts=data.get("max_attempts", 1),
            instructions=data.get("instructions", ""),
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentTemplateSerializer(template).data, status=status.HTTP_201_CREATED)


class TemplateDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.template.manage")]

    def get(self, request, template_id):
        inst = require_active_institution(request)
        template = get_object_or_404(
            AssessmentTemplate.objects.for_institution(inst).prefetch_related("versions__version_questions"),
            id=template_id,
        )
        return Response(AssessmentTemplateSerializer(template).data)

    def patch(self, request, template_id):
        inst = require_active_institution(request)
        template = get_object_or_404(AssessmentTemplate.objects.for_institution(inst), id=template_id)
        serializer = AssessmentTemplateUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        before = {"name": template.name, "status": template.status}
        if "name" in data:
            new_name = data["name"].strip()
            if AssessmentTemplate.objects.filter(institution=inst).exclude(id=template.id).filter(name__iexact=new_name).exists():
                raise ValidationError({"name": "An assessment template with this name already exists."})
            template.name = new_name
        if "description" in data:
            template.description = data["description"].strip()
        if "status" in data:
            template.status = data["status"]
        template.save()
        log_audit_event(
            action="ASSESSMENT_TEMPLATE_UPDATED",
            entity_type="AssessmentTemplate",
            entity_id=template.id,
            institution=inst,
            actor_user=request.user,
            before=before,
            after={"name": template.name, "status": template.status},
            request=request,
        )
        return Response(AssessmentTemplateSerializer(template).data)


class VersionDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.template.manage")]

    def get(self, request, version_id):
        inst = require_active_institution(request)
        version = get_object_or_404(
            AssessmentVersion.objects.for_institution(inst)
            .select_related("template")
            .prefetch_related("version_questions__question"),
            id=version_id,
        )
        return Response(AssessmentVersionSerializer(version).data)

    def patch(self, request, version_id):
        inst = require_active_institution(request)
        version = get_object_or_404(
            AssessmentVersion.objects.for_institution(inst).select_related("template"),
            id=version_id,
        )
        serializer = AssessmentVersionDraftUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = update_draft_version(
            version=version,
            data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentVersionSerializer(updated).data)


class VersionPublishView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.publish")]

    def post(self, request, version_id):
        inst = require_active_institution(request)
        version = get_object_or_404(
            AssessmentVersion.objects.for_institution(inst).select_related("template"),
            id=version_id,
        )
        published = publish_assessment_version(
            version=version,
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentVersionSerializer(published).data, status=status.HTTP_200_OK)


class VersionCloneView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.template.manage")]

    def post(self, request, version_id):
        inst = require_active_institution(request)
        version = get_object_or_404(
            AssessmentVersion.objects.for_institution(inst).select_related("template"),
            id=version_id,
        )
        cloned = clone_version_to_draft(
            source_version=version,
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentVersionSerializer(cloned).data, status=status.HTTP_201_CREATED)


class AssignmentListCreateView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.assign")]

    def get(self, request):
        inst = require_active_institution(request)
        qs = (
            AssessmentAssignment.objects.for_institution(inst)
            .select_related("assessment_version__template", "cohort__programme", "student_profile__membership__user")
            .annotate(attempt_count=Count("attempts", distinct=True))
            .order_by("-opens_at", "-created_at")
        )
        status_val = request.query_params.get("status", "").strip()
        if status_val:
            qs = qs.filter(status=status_val)
        return _paginate(qs, request, AssessmentAssignmentSerializer)

    def post(self, request):
        from apps.attempts.services import create_assessment_assignment

        inst = require_active_institution(request)
        serializer = AssessmentAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        assignment = create_assessment_assignment(
            institution=inst,
            assessment_version_id=data["assessment_version_id"],
            cohort_id=data.get("cohort_id"),
            student_profile_id=data.get("student_profile_id"),
            opens_at=data["opens_at"],
            closes_at=data["closes_at"],
            results_released=data.get("results_released", False),
            actor_user=request.user,
            request=request,
        )
        return Response(AssessmentAssignmentSerializer(assignment).data, status=status.HTTP_201_CREATED)


class AssignmentDetailView(APIView):
    permission_classes = [HasInstitutionPermission("assessment.assign")]

    def patch(self, request, assignment_id):
        inst = require_active_institution(request)
        assignment = get_object_or_404(AssessmentAssignment.objects.for_institution(inst), id=assignment_id)
        serializer = AssessmentAssignmentUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        before = {
            "status": assignment.status,
            "results_released": assignment.results_released,
            "opens_at": assignment.opens_at.isoformat(),
            "closes_at": assignment.closes_at.isoformat(),
        }
        for field in ("opens_at", "closes_at", "results_released", "status"):
            if field in data:
                setattr(assignment, field, data[field])
        try:
            assignment.save()
        except Exception as exc:
            raise ValidationError({"assignment": str(exc)})
        log_audit_event(
            action="ASSESSMENT_ASSIGNMENT_UPDATED",
            entity_type="AssessmentAssignment",
            entity_id=assignment.id,
            institution=inst,
            actor_user=request.user,
            before=before,
            after={
                "status": assignment.status,
                "results_released": assignment.results_released,
                "opens_at": assignment.opens_at.isoformat(),
                "closes_at": assignment.closes_at.isoformat(),
            },
            request=request,
        )
        return Response(AssessmentAssignmentSerializer(assignment).data)


class QuestionImportTemplateView(APIView):
    """Download sample XLSX or CSV template for bulk question authoring."""

    permission_classes = [HasInstitutionPermission("assessment.question.manage")]

    def get(self, request):
        fmt = request.query_params.get("export_format", "xlsx").strip().lower()
        if fmt == "csv":
            resp = HttpResponse(build_question_template_csv(), content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = 'attachment; filename="question_bank_template.csv"'
            return resp
        if fmt == "xlsx":
            resp = HttpResponse(
                build_question_template_xlsx(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            resp["Content-Disposition"] = 'attachment; filename="question_bank_template.xlsx"'
            return resp
        raise ValidationError({"export_format": "Format must be 'xlsx' or 'csv'."})


class QuestionBulkImportPreviewView(APIView):
    """Validate and preview uploaded XLSX/CSV question bank rows before committing."""

    permission_classes = [HasInstitutionPermission("assessment.question.manage")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        inst = require_active_institution(request)
        parsed = parse_and_validate_question_upload(institution=inst, uploaded_file=request.FILES.get("file"))
        return Response({"summary": parsed["summary"], "rows": parsed["rows"]})


class QuestionBulkImportCommitView(APIView):
    """Atomically commit validated XLSX/CSV questions into the active institution Question Bank."""

    permission_classes = [HasInstitutionPermission("assessment.question.manage")]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        inst = require_active_institution(request)
        mode = request.data.get("mode", "skip_invalid")
        result = commit_question_import(
            institution=inst,
            uploaded_file=request.FILES.get("file"),
            mode=mode,
            actor_user=request.user,
            request=request,
        )
        return Response(result, status=status.HTTP_201_CREATED)

