from openslides_backend.permissions.management_levels import (
    CommitteeManagementLevel,
    OrganizationManagementLevel,
)
from tests.system.action.base import BaseActionTestCase


class UserCreateActionTest(BaseActionTestCase):
    def permission_setup(self) -> None:
        self.create_meeting()
        self.user_id = self.create_user("test", group_ids=[1])
        self.login(self.user_id)

    def test_create(self) -> None:
        """
        Also checks if a default_password is generated and the correct hashed password stored
        """
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("user/2")
        assert model.get("username") == "test_Xcdfgee"
        assert model.get("default_password") is not None
        assert self.auth.is_equals(
            model.get("default_password", ""), model.get("password", "")
        )

    def test_create_first_and_last_name(self) -> None:
        response = self.request(
            "user.create",
            {
                "first_name": "John",
                "last_name": "Smith",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("user/2", {"username": "John Smith"})

    def test_create_first_name_and_count(self) -> None:
        self.set_models(
            {"user/2": {"username": "John"}, "user/3": {"username": "John 1"}}
        )
        response = self.request(
            "user.create",
            {
                "first_name": "John",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists("user/4", {"username": "John 2"})

    def test_create_some_more_fields(self) -> None:
        """
        Also checks if the correct password is stored from the given default_password
        """
        self.set_models(
            {
                "meeting/110": {"name": "name_DsJFXoot"},
                "meeting/111": {"name": "name_xXRGTLAJ"},
                "committee/78": {"name": "name_TSXpBGdt"},
                "committee/79": {"name": "name_hOldWvVF"},
            }
        )
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "default_vote_weight": "1.500000",
                "organization_management_level": "can_manage_users",
                "committee_ids": [78, 79],
                "default_password": "password",
            },
        )
        self.assert_status_code(response, 200)
        model = self.get_model("user/2")
        assert model.get("username") == "test_Xcdfgee"
        assert model.get("default_vote_weight") == "1.500000"
        assert model.get("committee_ids") == [78, 79]
        assert model.get("organization_management_level") == "can_manage_users"
        assert model.get("default_password") == "password"
        assert self.auth.is_equals(
            model.get("default_password", ""), model.get("password", "")
        )

    def test_create_template_fields(self) -> None:
        self.set_models(
            {
                "committee/1": {"name": "C1", "meeting_ids": [1]},
                "committee/2": {"name": "C2", "meeting_ids": [2]},
                "meeting/1": {"committee_id": 1},
                "meeting/2": {"committee_id": 2},
                "user/222": {"meeting_ids": [1]},
                "group/11": {"meeting_id": 1},
                "group/22": {"meeting_id": 2},
            }
        )
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "group_$_ids": {1: [11], 2: [22]},
                "vote_delegations_$_from_ids": {1: [222]},
                "comment_$": {1: "comment<iframe></iframe>"},
                "number_$": {2: "number"},
                "structure_level_$": {1: "level_1", 2: "level_2"},
                "about_me_$": {1: "<p>about</p><iframe></iframe>"},
                "vote_weight_$": {1: "1.000000", 2: "2.333333"},
                "committee_$_management_level": {
                    1: CommitteeManagementLevel.CAN_MANAGE,
                    2: None,
                },
                "committee_ids": [1, 2],
            },
        )
        self.assert_status_code(response, 200)
        user = self.get_model("user/223")
        assert (
            CommitteeManagementLevel(user.get("committee_$1_management_level"))
            == CommitteeManagementLevel.CAN_MANAGE
        )
        assert (
            CommitteeManagementLevel(user.get("committee_$2_management_level"))
            == CommitteeManagementLevel.NO_RIGHT
        )
        assert user.get("committee_ids") == [1, 2]
        assert user.get("group_$1_ids") == [11]
        assert user.get("group_$2_ids") == [22]
        assert set(user.get("group_$_ids", [])) == {"1", "2"}
        assert user.get("vote_delegations_$1_from_ids") == [222]
        assert user.get("vote_delegations_$_from_ids") == ["1"]
        assert user.get("comment_$1") == "comment&lt;iframe&gt;&lt;/iframe&gt;"
        assert user.get("comment_$") == ["1"]
        assert user.get("number_$2") == "number"
        assert user.get("number_$") == ["2"]
        assert user.get("structure_level_$1") == "level_1"
        assert user.get("structure_level_$2") == "level_2"
        assert set(user.get("structure_level_$", [])) == {"1", "2"}
        assert user.get("about_me_$1") == "<p>about</p>&lt;iframe&gt;&lt;/iframe&gt;"
        assert user.get("about_me_$") == ["1"]
        assert user.get("vote_weight_$1") == "1.000000"
        assert user.get("vote_weight_$2") == "2.333333"
        assert set(user.get("vote_weight_$", [])) == {"1", "2"}
        assert user.get("meeting_ids") == [1, 2]
        user = self.get_model("user/222")
        assert user.get("vote_delegated_$1_to_id") == 223
        assert user.get("vote_delegated_$_to_id") == ["1"]
        group1 = self.get_model("group/11")
        assert group1.get("user_ids") == [223]
        group2 = self.get_model("group/22")
        assert group2.get("user_ids") == [223]
        meeting = self.get_model("meeting/1")
        assert meeting.get("user_ids") == [223]
        meeting = self.get_model("meeting/2")
        assert meeting.get("user_ids") == [223]

    def test_invalid_template_field_replacement_invalid_committee(self) -> None:
        self.set_models(
            {
                "committee/1": {"name": "C1", "meeting_ids": [1]},
                "meeting/1": {"committee_id": 1},
                "user/222": {"meeting_ids": [1]},
            }
        )
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "committee_$_management_level": {
                    1: None,
                    2: CommitteeManagementLevel.CAN_MANAGE,
                },
                "committee_ids": [1, 2],
            },
        )
        self.assert_status_code(response, 400)
        self.assertIn("'committee/2' does not exist.", response.json["message"])

    def test_invalid_template_field_replacement_invalid_meeting(self) -> None:
        self.create_model("meeting/1")
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "comment_$": {2: "comment"},
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "'meeting/2' does not exist",
            response.json["message"],
        )

    def test_invalid_template_field_replacement_str(self) -> None:
        self.create_model("meeting/1")
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "comment_$": {"str": "comment"},
            },
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "data.comment_$ must not contain {'str'} properties",
            response.json["message"],
        )

    def test_create_invalid_group_id(self) -> None:
        self.set_models(
            {
                "meeting/1": {},
                "meeting/2": {},
                "group/11": {"meeting_id": 1},
            }
        )
        response = self.request(
            "user.create",
            {
                "username": "test_Xcdfgee",
                "group_$_ids": {2: [11]},
            },
        )
        self.assert_status_code(response, 400)

    def test_create_empty_data(self) -> None:
        response = self.request("user.create", {})
        self.assert_status_code(response, 400)
        assert "Need username or first_name or last_name" in response.json["message"]

    def test_create_wrong_field(self) -> None:
        response = self.request(
            "user.create", {"wrong_field": "text_AefohteiF8", "username": "test1"}
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "data must not contain {'wrong_field'} properties",
            response.json["message"],
        )

    def test_username_already_exists(self) -> None:
        response = self.request(
            "user.create",
            {
                "username": "admin",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 400)
        assert (
            response.json["message"] == "A user with the username admin already exists."
        )

    def test_user_create_with_empty_vote_delegation_from_ids(self) -> None:
        response = self.request(
            "user.create",
            {
                "username": "testname",
                "vote_delegations_$_from_ids": {},
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/2", {"username": "testname", "vote_delegations_$_from_ids": []}
        )

    def test_create_committe_manager_without_committee_ids(self) -> None:
        """Giving committee management level requires committee_ids"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "committee_$_management_level": {
                    "60": CommitteeManagementLevel.CAN_MANAGE,
                    "63": CommitteeManagementLevel.CAN_MANAGE,
                },
                "committee_ids": [63],
            },
        )
        self.assert_status_code(response, 400)
        self.assertIn(
            "You must add the user to the committee(s) '60', because you want to give him committee management level permissions.",
            response.json["message"],
        )

    def test_create_empty_username(self) -> None:
        response = self.request("user.create", {"username": ""})
        self.assert_status_code(response, 400)
        self.assertIn(
            "data.username must be longer than or equal to 1 characters",
            response.json["message"],
        )

    def test_create_user_without_explicit_scope(self) -> None:
        response = self.request("user.create", {"username": "user/2"})
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/2",
            {
                "meeting_ids": [],
                "organization_management_level": None,
                "committee_$_management_level": None,
            },
        )

    def test_create_permission_nothing(self) -> None:
        self.permission_setup()
        response = self.request(
            "user.create",
            {
                "username": "username",
                "vote_weight_$": {1: "1.000000"},
                "group_$_ids": {1: [1]},
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "The user needs OrganizationManagementLevel.can_manage_users or CommitteeManagementLevel.can_manage for committees of following meetings or Permission user.can_manage for meetings {1}",
            response.json["message"],
        )

    def test_create_permission_auth_error(self) -> None:
        self.permission_setup()
        response = self.request(
            "user.create",
            {
                "username": "username_Neu",
                "vote_weight_$": {1: "1.000000"},
                "group_$_ids": {1: [1]},
            },
            anonymous=True,
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "Anonymous is not allowed to execute user.create",
            response.json["message"],
        )

    def test_create_permission_superadmin(self) -> None:
        """
        SUPERADMIN may set fields of all groups and may set an other user as SUPERADMIN, too.
        The SUPERADMIN don't need to belong to a meeting in any way to change data!
        """
        self.permission_setup()
        self.set_organization_management_level(
            OrganizationManagementLevel.SUPERADMIN, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "username_new",
                "organization_management_level": OrganizationManagementLevel.SUPERADMIN,
                "vote_weight_$": {1: "1.000000"},
                "group_$_ids": {1: [1]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "username": "username_new",
                "organization_management_level": OrganizationManagementLevel.SUPERADMIN,
                "vote_weight_$": ["1"],
                "vote_weight_$1": "1.000000",
                "group_$_ids": ["1"],
                "group_$1_ids": [1],
                "meeting_ids": [1],
            },
        )

    def test_create_permission_group_A_oml_manage_user(self) -> None:
        """May create group A fields on organsisation scope, because belongs to 2 meetings in 2 committees, requiring OML level permission"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "new username",
                "title": "new title",
                "first_name": "new first_name",
                "last_name": "new last_name",
                "is_active": True,
                "is_physical_person": True,
                "default_password": "new default_password",
                "gender": "female",
                "email": "info@openslides.com ",
                "default_number": "new default_number",
                "default_structure_level": "new default_structure_level",
                "default_vote_weight": "1.234000",
                "group_$_ids": {"1": [1], "4": [4]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "username": "new username",
                "title": "new title",
                "first_name": "new first_name",
                "last_name": "new last_name",
                "is_active": True,
                "is_physical_person": True,
                "default_password": "new default_password",
                "gender": "female",
                "email": "info@openslides.com ",
                "default_number": "new default_number",
                "default_structure_level": "new default_structure_level",
                "default_vote_weight": "1.234000",
                "group_$1_ids": [1],
                "group_$4_ids": [4],
            },
        )

    def test_create_permission_group_A_cml_manage_user(self) -> None:
        """May create group A fields on cml scope"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.set_models(
            {
                f"user/{self.user_id}": {
                    "committee_$60_management_level": CommitteeManagementLevel.CAN_MANAGE,
                    "committee_$_management_level": ["60"],
                    "committee_ids": [60],
                },
                "meeting/4": {
                    "committee_id": 60,
                },
                "committee/60": {"meeting_ids": [1, 4]},
            }
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {"1": [1], "4": [4]},
                "committee_ids": [60],
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "username": "usersname",
                "group_$1_ids": [1],
                "group_$4_ids": [4],
                "committee_ids": [60],
            },
        )

    def test_create_permission_group_A_user_can_manage(self) -> None:
        """May create group A fields on meeting scope"""
        self.permission_setup()
        self.set_user_groups(self.user_id, [2])
        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {"1": [1]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "username": "usersname",
                "group_$1_ids": [1],
            },
        )

    def test_create_permission_group_A_no_permission(self) -> None:
        """May not create group A fields on organsisation scope, although having both committee permissions"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.update_model(
            f"user/{self.user_id}",
            {
                "committee_$60_management_level": CommitteeManagementLevel.CAN_MANAGE,
                "committee_$63_management_level": CommitteeManagementLevel.CAN_MANAGE,
                "committee_$_management_level": ["60", "63"],
                "committee_ids": [60, 63],
            },
        )

        response = self.request(
            "user.create",
            {
                "username": "new username",
                "committee_ids": [60],
                "group_$_ids": {"4": [4]},
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "You are not allowed to perform action user.create. Missing permission: OrganizationManagementLevel can_manage_users in organization 1",
            response.json["message"],
        )

    def test_create_permission_group_B_user_can_manage(self) -> None:
        """create group B fields with simple user.can_manage permissions"""
        self.permission_setup()
        self.set_organization_management_level(None, self.user_id)
        self.set_user_groups(self.user_id, [2])  # Admin groups of meeting/1

        self.set_models(
            {
                "user/5": {"username": "user5", "meeting_ids": [1]},
                "user/6": {"username": "user6", "meeting_ids": [1]},
            }
        )

        response = self.request(
            "user.create",
            {
                "username": "username7",
                "number_$": {"1": "number1"},
                "structure_level_$": {"1": "structure_level 1"},
                "vote_weight_$": {"1": "12.002345"},
                "about_me_$": {"1": "about me 1"},
                "comment_$": {"1": "comment zu meeting/1"},
                "vote_delegations_$_from_ids": {"1": [5, 6]},
                "group_$_ids": {"1": [1]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/7",
            {
                "username": "username7",
                "number_$": ["1"],
                "number_$1": "number1",
                "structure_level_$": ["1"],
                "structure_level_$1": "structure_level 1",
                "vote_weight_$": ["1"],
                "vote_weight_$1": "12.002345",
                "about_me_$": ["1"],
                "about_me_$1": "about me 1",
                "comment_$": ["1"],
                "comment_$1": "comment zu meeting/1",
                "vote_delegations_$_from_ids": ["1"],
                "vote_delegations_$1_from_ids": [5, 6],
                "meeting_ids": [1],
            },
        )

    def test_create_permission_group_B_user_can_manage_no_permission(self) -> None:
        """Group B fields needs explicit user.can_manage permission for meeting"""
        self.permission_setup()
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )
        self.set_user_groups(self.user_id, [3])  # Empty group of meeting/1

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "number_$": {"1": "number1"},
                "group_$_ids": {"1": [1]},
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "You are not allowed to perform action user.create. Missing permission: Permission user.can_manage in meeting 1",
            response.json["message"],
        )

    def test_create_permission_group_C_oml_manager(self) -> None:
        """May create group C group_$_ids by OML permission"""
        self.permission_setup()
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {1: [1]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {"group_$_ids": ["1"], "group_$1_ids": [1], "username": "usersname"},
        )

    def test_create_permission_group_C_committee_manager(self) -> None:
        """May create group C group_$_ids by committee permission"""
        self.permission_setup()
        self.set_committee_management_level([60], self.user_id)

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {1: [1]},
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {"group_$_ids": ["1"], "group_$1_ids": [1], "username": "usersname"},
        )

    def test_create_permission_group_C_user_can_manage(self) -> None:
        """May create group C group_$_ids by user.can_manage permission"""
        self.permission_setup()
        self.set_user_groups(self.user_id, [2])  # Admin-group

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {1: [2]},
            },
        )

        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "username": "usersname",
                "group_$_ids": ["1"],
                "group_$1_ids": [2],
                "meeting_ids": [1],
            },
        )

    def test_create_permission_group_C_no_permission(self) -> None:
        """May not create group C group_$_ids"""
        self.permission_setup()

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "group_$_ids": {1: [1]},
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "The user needs OrganizationManagementLevel.can_manage_users or CommitteeManagementLevel.can_manage for committees of following meetings or Permission user.can_manage for meetings {1}",
            response.json["message"],
        )

    def test_create_permission_group_D_permission_with_OML(self) -> None:
        """May create Group D committee fields with OML level permission for more than one committee"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "committee_$_management_level": {
                    "60": CommitteeManagementLevel.CAN_MANAGE,
                    "63": CommitteeManagementLevel.CAN_MANAGE,
                },
                "committee_ids": [60, 63],
                "organization_management_level": None,
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "committee_ids": [60, 63],
                "committee_$60_management_level": CommitteeManagementLevel.CAN_MANAGE,
                "committee_$63_management_level": CommitteeManagementLevel.CAN_MANAGE,
                "organization_management_level": None,
                "username": "usersname",
            },
        )
        user3 = self.get_model("user/3")
        assert user3.get("organization_management_level") is None
        assert (
            OrganizationManagementLevel(user3.get("organization_management_level"))
            == OrganizationManagementLevel.NO_RIGHT
        )

    def test_create_permission_group_D_permission_with_CML(self) -> None:
        """
        May create Group D committee fields with CML permission for one committee only.
        Note: For 2 committees he can't set the username, which is required, but within 2 committees
        it would be organizational scope with organizational rights required.
        To do this he could create a user with 1 committee and later he could update the
        same user with second committee, if he has the permission for the committees.
        """
        self.permission_setup()
        self.set_committee_management_level([60], self.user_id)

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "committee_$_management_level": {
                    "60": CommitteeManagementLevel.CAN_MANAGE,
                },
                "committee_ids": [60],
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "committee_ids": [60],
                "committee_$60_management_level": CommitteeManagementLevel.CAN_MANAGE,
                "username": "usersname",
            },
        )

    def test_create_permission_group_D_no_permission(self) -> None:
        """May not create Group D committee fields, because of missing CML permission for one committee"""
        self.permission_setup()
        self.create_meeting(base=4)
        self.set_committee_management_level([60], self.user_id)

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "committee_$_management_level": {
                    "60": CommitteeManagementLevel.CAN_MANAGE,
                    "63": CommitteeManagementLevel.CAN_MANAGE,
                },
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "You are not allowed to perform action user.create. Missing permission: CommitteeManagementLevel can_manage in committee 63",
            response.json["message"],
        )

    def test_create_permission_group_E_OML_high_enough(self) -> None:
        """OML level to set is sufficient"""
        self.permission_setup()
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 200)
        self.assert_model_exists(
            "user/3",
            {
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
                "username": "usersname",
            },
        )

    def test_create_permission_group_E_OML_not_high_enough(self) -> None:
        """OML level to set is higher than level of request user"""
        self.permission_setup()
        self.set_organization_management_level(
            OrganizationManagementLevel.CAN_MANAGE_USERS, self.user_id
        )

        response = self.request(
            "user.create",
            {
                "username": "usersname",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_ORGANIZATION,
            },
        )
        self.assert_status_code(response, 403)
        self.assertIn(
            "Your organization management level is not high enough to set a Level of can_manage_organization!",
            response.json["message"],
        )

    def test_create_demo_user(self) -> None:
        """demo_user only with user.update"""
        self.permission_setup()

        response = self.request(
            "user.create",
            {
                "is_demo_user": True,
            },
        )

        self.assert_status_code(response, 400)
        self.assertIn(
            "data must not contain {'is_demo_user'} properties",
            response.json["message"],
        )

    def test_create_forbidden_username(self) -> None:
        response = self.request(
            "user.create",
            {
                "username": "   ",
                "organization_management_level": OrganizationManagementLevel.CAN_MANAGE_USERS,
            },
        )
        self.assert_status_code(response, 400)
        assert "This username is forbidden." in response.json["message"]
