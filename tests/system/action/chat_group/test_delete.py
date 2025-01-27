from typing import Any, Dict

from openslides_backend.permissions.permissions import Permissions
from tests.system.action.base import BaseActionTestCase


class ChatGroupDelete(BaseActionTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.test_models: Dict[str, Dict[str, Any]] = {
            "organization/1": {"enable_chat": True},
            "meeting/1": {"enable_chat": True, "is_active_in_organization_id": 1},
            "chat_group/1": {"meeting_id": 1, "name": "redekreis1"},
        }

    def test_delete(self) -> None:
        self.set_models(self.test_models)
        response = self.request("chat_group.delete", {"id": 1})
        self.assert_status_code(response, 200)
        self.assert_model_deleted("chat_group/1")

    def test_delete_not_enabled(self) -> None:
        self.test_models["meeting/1"]["enable_chat"] = False
        self.set_models(self.test_models)
        response = self.request("chat_group.delete", {"id": 1})
        self.assert_status_code(response, 400)
        assert "Chat is not enabled." in response.json["message"]

    def test_delete_not_enabled_in_organization(self) -> None:
        self.test_models["organization/1"]["enable_chat"] = False
        self.set_models(self.test_models)
        response = self.request("chat_group.delete", {"id": 1})
        self.assert_status_code(response, 400)
        assert "Chat is not enabled." in response.json["message"]

    def test_delete_no_permissions(self) -> None:
        self.base_permission_test(self.test_models, "chat_group.delete", {"id": 1})

    def test_delete_permissions(self) -> None:
        self.base_permission_test(
            self.test_models,
            "chat_group.delete",
            {"id": 1},
            Permissions.Chat.CAN_MANAGE,
        )
