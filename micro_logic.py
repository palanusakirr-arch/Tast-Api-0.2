from typing import Any, Optional, Tuple


class MicroLogic:

    def __init__(self, data_class: Any) -> None:
        self.data_class: Any = data_class
        
    def logic_create(
        self,
        user_id: int,
        item_names: list[str],
        item_quantity: list[float | int],
        item_costs_per_unit: list[float],
        items_arrived_date: list[str],
        discount_start_date: list[str | None],
        discount_end_date: list[str | None],
        discount_percentage: list[float | None],
        barcode_list: list[str],
        status_list: list[str],
    ) -> bool | dict[str, Any]:
        # Level Zero
        item_total_costs = [price * quantity for price, quantity in zip(item_costs_per_unit, item_quantity)]
        action: Any = self.data_class.db_create(
            user_id,
            item_names,
            item_quantity,
            item_costs_per_unit,
            item_total_costs,
            items_arrived_date,
            discount_start_date,
            discount_end_date,
            discount_percentage,
            barcode_list,
            status_list,
        )
        if action and isinstance(action, dict):
            return action 
        return True
        
    def logic_show(
        self,
        user_id: int
        ) -> list[Tuple[Any, ...]] | dict[str, str]:
        # Level Zero
        action: Any = self.data_class.db_show(
            user_id
            )
        return action        
        
    def logic_update(
        self,
        user_id: int,
        field_names: list[str],
        update_values: list[Any],
        identifier_names: list[str],
        identifier_values: list[Any],
    ) -> bool | dict[str, Any]:
        # Level Zero
        action: Any = self.data_class.db_update(
            user_id,
            field_names,
            update_values,
            identifier_names,
            identifier_values,
        )
        if action and isinstance(action, dict):
            return action
        return True
        
    def logic_delete(
        self,
        user_id: int,
        id_list: list[int],
    ) -> bool | dict[str, Any]:
        # Level Zero 
        action: Any = self.data_class.db_delete(user_id, id_list)
        if action and isinstance(action, dict):
            return action
        return True
        