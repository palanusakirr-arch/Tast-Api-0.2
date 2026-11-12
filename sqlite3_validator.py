from datetime import date
from typing import Any, Optional, Type


class DataBaseValidator:

    def __init__(self) -> None:
        self.type_list: list[Type[Any]] = [str, int, float, date]

    def create_helper(
        self,
        outer_list: list[Any],
        allowed_column: Optional[list[str]] = None,
    ) -> bool | dict[str, str]:
        # Level Medium 
        length_limit: int = len(outer_list[0])
        for item in outer_list:
            if len(item) != length_limit:
                return {
                    "error": "ValueError",
                    "reason": "please check length of all lists",
                    "code": "create_helper_A",
                    "semantic": "invalid_length",
                }
            for val in item:
                if type(val) not in self.type_list:
                    return {
                        "error": "TypeError",
                        "reason": "please enter valid type such as str, int, float.",
                        "code": "create_helper_B",
                        "semantic": "invalid_type",
                    }
        return True


    def update_helper(
        self,
        main_list: list[Any],
        secondary_list: list[Any],
        allowed_column: list[str],
    ) -> bool | dict[str, str]:
        length_limit: int = len(main_list[0])
        for item, item2 in zip(main_list, secondary_list):
            # Level Easy
            if len(item) != length_limit:
                return {
                    "error": "ValueError",
                    "reason": "please check length properly",
                    "code": "update_helper_A",
                    "semantic": "invalid_length",
                }
            if len(item2) != length_limit:
                return {
                    "error": "ValueError",
                    "reason": "please check length properly",
                    "code": "update_helper_B",
                    "semantic": "invalid_length",
                }
            if not set(item).issubset(allowed_column):
                return {
                    "error": "ValueError",
                    "reason": "please check all values of list properly",
                    "code": "update_helper_C",
                    "semantic": "unpermitted_values",
                }
            if "id" in item[0]:
                return {
                    "error": "TypeError",
                    "reason": "you cannot update id of product",
                    "code": "update_helper_D",
                    "semantic": "updation_of_unpermitted_field_attempted",
                }
        return True
        