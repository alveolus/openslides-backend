from typing import Any, Iterable

import fastjsonschema  # type: ignore
from fastjsonschema import JsonSchemaException  # type: ignore

from ...models.topic import Topic
from ...shared.exceptions import ActionException, PermissionDenied
from ...shared.interfaces import Event, WriteRequestElement
from ...shared.patterns import FullQualifiedField, FullQualifiedId
from ...shared.permissions.topic import TOPIC_CAN_MANAGE
from ...shared.schema import schema_version
from ..actions import register_action
from ..actions_interface import Payload
from ..base import Action, DataSet, merge_write_request_elements

is_valid_new_topic = fastjsonschema.compile(
    {
        "$schema": schema_version,
        "title": "New topics schema",
        "description": "An array of new topics.",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "meeting_id": Topic().get_schema("meeting_id"),
                "title": Topic().get_schema("title"),
                "text": Topic().get_schema("text"),
                "mediafile_attachment_ids": Topic().get_schema(
                    "mediafile_attachment_ids"
                ),
            },
            "required": ["meeting_id", "title"],
        },
        "minItems": 1,
    }
)


@register_action("topic.create")
class TopicCreate(Action):
    """
    Action to create simple topics that can be shown in the agenda.
    """

    model = Topic()

    def check_permission_on_entry(self) -> None:
        if not self.permission.has_perm(self.user_id, TOPIC_CAN_MANAGE):
            raise PermissionDenied(f"User does not have {TOPIC_CAN_MANAGE} permission.")

    def validate(self, payload: Payload) -> None:
        try:
            is_valid_new_topic(payload)
        except JsonSchemaException as exception:
            raise ActionException(exception.message)

    def prepare_dataset(self, payload: Payload) -> DataSet:
        data = []
        for topic in payload:
            id, position = self.database.getId(collection=self.model.collection)
            self.set_min_position(position)
            references = self.get_references(
                model=self.model,
                id=id,
                obj=topic,
                fields=["meeting_id", "mediafile_attachment_ids"],
            )
            data.append({"topic": topic, "new_id": id, "references": references})
        return {"position": self.position, "data": data}

    def create_write_request_elements(
        self, dataset: DataSet
    ) -> Iterable[WriteRequestElement]:
        position = dataset["position"]
        for element in dataset["data"]:
            topic_write_request_element = self.create_topic_write_request_element(
                position, element
            )
            for reference in self.get_references_updates(position, element):
                topic_write_request_element = merge_write_request_elements(
                    (topic_write_request_element, reference)
                )
            yield topic_write_request_element

    def create_topic_write_request_element(
        self, position: int, element: Any
    ) -> WriteRequestElement:
        fqfields = {}

        # Title
        fqfields[
            FullQualifiedField(self.model.collection, element["new_id"], "title")
        ] = element["topic"]["title"]

        # Text
        text = element["topic"].get("text")
        if text is not None:
            fqfields[
                FullQualifiedField(self.model.collection, element["new_id"], "text")
            ] = text

        # Mediafile attachments
        mediafile_attachment_ids = element["topic"].get("mediafile_attachment_ids")
        if mediafile_attachment_ids:
            fqfields[
                FullQualifiedField(
                    self.model.collection, element["new_id"], "mediafile_attachment_ids"
                )
            ] = mediafile_attachment_ids

        information = {
            FullQualifiedId(self.model.collection, element["new_id"]): ["Topic created"]
        }
        event = Event(type="create", fqfields=fqfields)
        return WriteRequestElement(
            events=[event],
            information=information,
            user_id=self.user_id,
            locked_fields={},
        )

    def get_references_updates(
        self, position: int, element: Any
    ) -> Iterable[WriteRequestElement]:
        for fqfield, data in element["references"].items():
            event = Event(type="update", fqfields={fqfield: data["value"]})
            yield WriteRequestElement(
                events=[event],
                information={
                    FullQualifiedId(fqfield.collection, fqfield.id): [
                        "Object attached to new topic"
                    ]
                },
                user_id=self.user_id,
                locked_fields={fqfield: position},
            )