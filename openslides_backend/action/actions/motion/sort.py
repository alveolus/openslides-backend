from ....models.models import Motion
from ....permissions.permissions import Permissions
from ...generics.update import UpdateAction
from ...mixins.singular_action_mixin import SingularActionMixin
from ...mixins.tree_sort_mixin import TreeSortMixin
from ...util.default_schema import DefaultSchema
from ...util.register import register_action
from ...util.typing import ActionData


@register_action("motion.sort")
class MotionSort(TreeSortMixin, SingularActionMixin, UpdateAction):
    """
    Action to sort motions.
    """

    model = Motion()
    schema = DefaultSchema(Motion()).get_tree_sort_schema()
    permission = Permissions.Motion.CAN_MANAGE

    def get_updated_instances(self, action_data: ActionData) -> ActionData:
        action_data = super().get_updated_instances(action_data)
        # Action data is an iterable with exactly one item
        instance = next(iter(action_data))
        yield from self.sort_tree(
            nodes=instance["tree"],
            meeting_id=instance["meeting_id"],
            weight_key="sort_weight",
            parent_id_key="sort_parent_id",
            children_ids_key="sort_children_ids",
        )
