from typing import Any, Dict, Iterable, List

from ...models.models import Motion
from ...shared.exceptions import ActionException
from ...shared.interfaces import WriteRequestElement
from ...shared.patterns import ID_REGEX, Collection, FullQualifiedId
from ...shared.schema import id_list_schema, optional_id_schema
from ..agenda_item.agenda_creation import (
    CreateActionWithAgendaItemMixin,
    agenda_creation_properties,
)
from ..agenda_item.create import AgendaItemCreate
from ..base import DataSet
from ..create_action_with_dependencies import CreateActionWithDependencies
from ..default_schema import DefaultSchema
from ..motion_submitter.create import MotionSubmitterCreateAction
from ..register import register_action


@register_action("motion.create")
class MotionCreate(CreateActionWithDependencies, CreateActionWithAgendaItemMixin):
    """
    Create Action for motions.
    """

    model = Motion()
    schema = DefaultSchema(Motion()).get_create_schema(
        optional_properties=[
            "meeting_id",
            "title",
            "number",
            "state_extension",
            "sort_parent_id",
            "category_id",
            "block_id",
            "supporter_ids",
            "tag_ids",
            "attachment_ids",
            "origin_id",
            "text",
            "lead_motion_id",
            "statute_paragraph_id",
            "reason",
        ],
        required_properties=["meeting_id", "title"],
        additional_optional_fields={
            "workflow_id": optional_id_schema,
            "amendment_paragraphs": {
                "type": "object",
                "patternProperties": {ID_REGEX: {"type": "string"}},
                "additionalProperties": False,
            },
            "submitter_ids": id_list_schema,
            **agenda_creation_properties,
        },
    )
    dependencies = [AgendaItemCreate]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.additional_write_requests: List[WriteRequestElement] = []

    def update_instance(self, instance: Dict[str, Any]) -> Dict[str, Any]:
        # special check logic
        if instance.get("lead_motion_id"):
            if instance.get("statute_paragraph_id"):
                raise ActionException(
                    "You can't give both of lead_motion_id and statute_paragraph_id."
                )
            if not instance.get("text") and not instance.get("amendment_paragraphs"):
                raise ActionException(
                    "Text or amendment_paragraphs is required in this context."
                )
            if instance.get("text") and instance.get("amendment_paragraphs"):
                raise ActionException(
                    "You can't give both of text and amendment_paragraphs"
                )
            if instance.get("text") and "amendment_paragraphs" in instance:
                del instance["amendment_paragraphs"]
            if instance.get("amendment_paragraphs") and "text" in instance:
                del instance["text"]
        else:
            if not instance.get("text"):
                raise ActionException("Text is required")
            if instance.get("amendment_paragraphs"):
                raise ActionException(
                    "You can't give amendment_paragraphs in this context"
                )

        # fetch all needed settings and check reason
        meeting = self.database.get(
            FullQualifiedId(Collection("meeting"), instance["meeting_id"]),
            [
                "motions_default_workflow_id",
                "motions_default_amendment_workflow_id",
                "motions_default_statute_amendment_workflow_id",
                "motions_reason_required",
            ],
        )
        if meeting.get("motions_reason_required") and not instance.get("reason"):
            raise ActionException("Reason is required")

        # calculate state_id from workflow_id
        workflow_id = instance.pop("workflow_id", None)
        if workflow_id is None:
            if instance.get("lead_motion_id"):
                workflow_id = meeting.get("motions_default_amendment_workflow_id")
            elif instance.get("statute_paragraph_id"):
                workflow_id = meeting.get(
                    "motions_default_statute_amendment_workflow_id"
                )
            else:
                workflow_id = meeting.get("motions_default_workflow_id")
        if workflow_id:
            workflow = self.database.get(
                FullQualifiedId(Collection("motion_workflow"), workflow_id),
                ["first_state_id"],
            )
            instance["state_id"] = workflow.get("first_state_id")
        else:
            raise ActionException(
                "No matching default workflow defined on this meeting"
            )

        # check for origin_id
        if instance.get("origin_id"):
            meeting = self.database.get(
                FullQualifiedId(Collection("meeting"), instance["meeting_id"]),
                ["committee_id"],
            )
            forwarded_from = self.database.get(
                FullQualifiedId(Collection("motion"), instance["origin_id"]),
                ["meeting_id"],
            )
            forwarded_from_meeting = self.database.get(
                FullQualifiedId(Collection("meeting"), forwarded_from["meeting_id"]),
                ["committee_id"],
            )
            committee = self.database.get(
                FullQualifiedId(
                    Collection("committee"), forwarded_from_meeting["committee_id"]
                ),
                ["forward_to_committee_ids"],
            )
            if meeting["committee_id"] not in committee.get(
                "forward_to_committee_ids", []
            ):
                raise ActionException(
                    f"Committee id {meeting['committee_id']} not in {committee.get('forward_to_committee_ids', [])}"
                )

        # replace amendment_paragraphs
        if instance.get("amendment_paragraphs"):
            amendment_paragraphs = instance.pop("amendment_paragraphs")
            for paragraph_number, text in amendment_paragraphs.items():
                instance[f"amendment_paragraph_${paragraph_number}"] = text

        # create submitters
        submitter_ids = instance.pop("submitter_ids", None)
        if submitter_ids:
            action = MotionSubmitterCreateAction(
                self.permission,
                self.database,
                {FullQualifiedId(self.model.collection, instance["id"]): instance},
            )
            payload = []
            for user_id in submitter_ids:
                payload.append({"motion_id": instance["id"], "user_id": user_id})
            result = action.perform(payload, self.user_id)
            self.additional_write_requests.extend(result)

        return instance

    def create_write_request_elements(
        self, dataset: DataSet
    ) -> Iterable[WriteRequestElement]:
        # first write motion, then submitters
        yield from super().create_write_request_elements(dataset)
        yield from self.additional_write_requests
