from openslides_backend.models.models import AgendaItem
from openslides_backend.permissions.permissions import Permissions
from tests.system.action.base import BaseActionTestCase


class AgendaItemSystemTest(BaseActionTestCase):
    def test_create(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
            }
        )
        response = self.request("agenda_item.create", {"content_object_id": "topic/1"})
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/1")
        self.assertFalse(model.get("meta_deleted"))
        self.assertEqual(model.get("meeting_id"), 2)
        self.assertEqual(model.get("content_object_id"), "topic/1")
        self.assertEqual(model.get("type"), AgendaItem.AGENDA_ITEM)
        self.assertEqual(model.get("weight"), 10000)
        self.assertEqual(model.get("level"), 0)

        model = self.get_model("meeting/2")
        self.assertEqual(model.get("agenda_item_ids"), [1])

        model = self.get_model("topic/1")
        self.assertEqual(model.get("agenda_item_id"), 1)

    def test_create_more_fields(self) -> None:
        self.set_models(
            {
                "meeting/1": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 1},
                "agenda_item/42": {"comment": "test", "meeting_id": 1},
            }
        )
        response = self.request(
            "agenda_item.create",
            {
                "content_object_id": "topic/1",
                "comment": "test_comment_oiuoitesfd",
                "type": AgendaItem.INTERNAL_ITEM,
                "parent_id": 42,
                "duration": 360,
            },
        )
        self.assert_status_code(response, 200)
        agenda_item = self.get_model("agenda_item/43")
        self.assertEqual(agenda_item["comment"], "test_comment_oiuoitesfd")
        self.assertEqual(agenda_item["type"], "internal")
        self.assertEqual(agenda_item["parent_id"], 42)
        self.assertEqual(agenda_item["duration"], 360)
        self.assertEqual(agenda_item["weight"], 1)
        self.assertFalse(agenda_item.get("closed"))
        assert agenda_item.get("level") == 1

    def test_create_parent_weight(self) -> None:
        self.set_models(
            {
                "meeting/1": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 1},
                "agenda_item/42": {"comment": "test", "meeting_id": 1, "weight": 10},
            }
        )
        response = self.request_multi(
            "agenda_item.create",
            [
                {
                    "content_object_id": "topic/1",
                    "parent_id": 42,
                },
                {
                    "content_object_id": "topic/1",
                    "parent_id": 42,
                },
            ],
        )
        self.assert_status_code(response, 200)
        agenda_item = self.get_model("agenda_item/43")
        self.assertEqual(agenda_item["parent_id"], 42)
        self.assertEqual(agenda_item["weight"], 1)
        agenda_item = self.get_model("agenda_item/44")
        self.assertEqual(agenda_item["parent_id"], 42)
        self.assertEqual(agenda_item["weight"], 2)

    def test_create_content_object_does_not_exist(self) -> None:
        response = self.request("agenda_item.create", {"content_object_id": "topic/1"})
        self.assert_status_code(response, 400)
        self.assert_model_not_exists("agenda_item/1")

    def test_create_differing_meeting_ids(self) -> None:
        self.set_models(
            {
                "meeting/1": {"is_active_in_organization_id": 1},
                "meeting/2": {"is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 1},
                "agenda_item/1": {"meeting_id": 2},
            }
        )
        response = self.request(
            "agenda_item.create", {"content_object_id": "topic/1", "parent_id": 1}
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "The following models do not belong to meeting 1: ['agenda_item/1']",
            response.json["message"],
        )
        self.assert_model_not_exists("agenda_item/2")

    def test_create_meeting_does_not_exist(self) -> None:
        self.create_model("topic/1", {"meeting_id": 2})
        response = self.request("agenda_item.create", {"content_object_id": "topic/1"})
        self.assert_status_code(response, 400)
        self.assert_model_not_exists("agenda_item/1")

    def test_create_no_meeting_id(self) -> None:
        self.create_model("topic/1")
        response = self.request("agenda_item.create", {"content_object_id": "topic/1"})
        self.assert_status_code(response, 400)
        self.assert_model_not_exists("agenda_item/1")

    def test_create_calc_fields_no_parent_agenda_type(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
            }
        )
        response = self.request(
            "agenda_item.create",
            {"content_object_id": "topic/1", "type": AgendaItem.AGENDA_ITEM},
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/1")
        assert model.get("is_internal") is False
        assert model.get("is_hidden") is False
        assert model.get("level") == 0

    def test_create_calc_fields_no_parent_hidden_type(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
            }
        )
        response = self.request(
            "agenda_item.create",
            {"content_object_id": "topic/1", "type": AgendaItem.HIDDEN_ITEM},
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/1")
        assert model.get("is_internal") is False
        assert model.get("is_hidden") is True
        assert model.get("level") == 0

    def test_create_calc_fields_no_parent_internal_type(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
                "topic/2": {"meeting_id": 2},
            }
        )
        response = self.request(
            "agenda_item.create",
            {
                "content_object_id": "topic/1",
                "type": AgendaItem.INTERNAL_ITEM,
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/1")
        assert model.get("is_internal") is True
        assert model.get("is_hidden") is False
        assert model.get("level") == 0

    def test_create_calc_fields_parent_agenda_internal(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
                "agenda_item/3": {
                    "content_object_id": "topic/2",
                    "type": AgendaItem.AGENDA_ITEM,
                    "meeting_id": 2,
                    "is_internal": False,
                    "is_hidden": False,
                    "level": 0,
                },
            }
        )
        response = self.request(
            "agenda_item.create",
            {
                "content_object_id": "topic/1",
                "type": AgendaItem.INTERNAL_ITEM,
                "parent_id": 3,
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/4")
        assert model.get("is_internal") is True
        assert model.get("is_hidden") is False
        assert model.get("level") == 1

    def test_create_calc_fields_parent_internal_internal(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
                "agenda_item/3": {
                    "content_object_id": "topic/2",
                    "type": AgendaItem.INTERNAL_ITEM,
                    "meeting_id": 2,
                    "is_internal": True,
                    "is_hidden": False,
                },
            }
        )
        response = self.request(
            "agenda_item.create",
            {
                "content_object_id": "topic/1",
                "type": AgendaItem.INTERNAL_ITEM,
                "parent_id": 3,
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/4")
        assert model.get("is_internal") is True
        assert model.get("is_hidden") is False
        assert model.get("level") == 1

    def test_create_calc_fields_parent_internal_hidden(self) -> None:
        self.set_models(
            {
                "meeting/2": {"name": "test", "is_active_in_organization_id": 1},
                "topic/1": {"meeting_id": 2},
                "agenda_item/3": {
                    "content_object_id": "topic/2",
                    "type": AgendaItem.INTERNAL_ITEM,
                    "meeting_id": 2,
                    "is_internal": True,
                    "is_hidden": False,
                    "level": 12,
                },
            }
        )
        response = self.request(
            "agenda_item.create",
            {
                "content_object_id": "topic/1",
                "type": AgendaItem.HIDDEN_ITEM,
                "parent_id": 3,
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("agenda_item/4")
        assert model.get("is_internal") is True
        assert model.get("is_hidden") is True
        assert model.get("level") == 13

    def test_create_no_permissions(self) -> None:
        self.base_permission_test(
            {"topic/1": {"meeting_id": 1}},
            "agenda_item.create",
            {"content_object_id": "topic/1"},
        )

    def test_create_permissions(self) -> None:
        self.base_permission_test(
            {"topic/1": {"meeting_id": 1}},
            "agenda_item.create",
            {"content_object_id": "topic/1"},
            Permissions.AgendaItem.CAN_MANAGE,
        )

    def test_create_replace_reverse_of_multi_content_object_id_required_error(
        self,
    ) -> None:
        self.set_models(
            {
                "meeting/1": {"name": "test", "is_active_in_organization_id": 1},
                "assignment/1": {"meeting_id": 1, "agenda_item_id": 1},
                "agenda_item/1": {"meeting_id": 1, "content_object_id": "assignment/1"},
            }
        )
        response = self.request(
            "agenda_item.create", {"content_object_id": "assignment/1"}
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "Update of agenda_item/1: You try to set following required fields to an empty value: ['content_object_id']",
            response.json["message"],
        )
        self.assert_model_exists("assignment/1", {"agenda_item_id": 1})
        self.assert_model_exists("agenda_item/1", {"content_object_id": "assignment/1"})
        self.assert_model_not_exists("agenda_item/2")
