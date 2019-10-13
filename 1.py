# Better way


def check_slots(search_str: str, index: int, slots: list) -> int:
    # we are going to find max length word in slots for current position
    # and returns len of this or -1 if it doesn't exists
    for slot in slots:
        i = index
        slot_len = len(slot)

        for j in range(slot_len):
            if slot[j] != search_str[i]:
                break
            else:
                i += 1
                # slot is too large
                if i == len(search_str):
                    break

        if i - index == slot_len:
            return slot_len

    return -1


def is_matching_obj(obj: dict, search_str: str):
    search_str = search_str.lower()
    phrase_str = obj["phrase"].lower()
    slots = sorted(obj["slots"], key=lambda slot: len(slot), reverse=True)
    slots = [slot.lower() for slot in slots]

    phrase_str_len = len(phrase_str)
    search_str_len = len(search_str)
    i = j = 0

    while i < search_str_len and j < phrase_str_len:
        if phrase_str[j] != search_str[i]:
            if phrase_str[j] == '{':
                slot_len = check_slots(search_str, i, slots)

                # match or not
                if slot_len == -1:
                    return False

                # get position after '}' in phrase_str
                while phrase_str[j] != '}':
                    j += 1
                    if j == phrase_str_len:
                        return False
                j += 1

                # get correct position in search_str
                i += slot_len
            else:
                j += 1
                i = 0
        else:
            i += 1
            j += 1

    return i == search_str_len


def phrase_search(object_list: list, search_string: str) -> int:
    for obj in object_list:
        if is_matching_obj(obj, search_string):
            return obj["id"]

    return 0


if __name__ == "__main__":
    """ 
    len(object) != 0
    object["id"] > 0
    0 <= len(object["phrase"]) <= 120
    0 <= len(object["slots"]) <= 50
    """
    object = [
        {"id": 1, "phrase": "Hello world!", "slots": []},
        {"id": 2, "phrase": "Yes, I wanna {pizza}", "slots": ["pizza", "BBQ", "pASta"]},
        {"id": 3, "phrase": "Give me your power", "slots": ["money", "gun"]},
        {"id": 4, "phrase": "FOO, BAR, I wanna {eat} and {drink}, FOO, BAR", "slots": ["pizza", "BBQ", "pepsi", "tea"]},
        {"id": 5, "phrase": "{I} want{s} {eat} and {drink}", "slots": ["pizza", "pepsi", "He", "I", "s", ""]},
        {"id": 6, "phrase": "Want {eat} and {drink", "slots": ["pizza", "pepsi"]},
    ]
    # default asserts
    assert phrase_search(object, 'I wanna pasta') == 2
    assert phrase_search(object, 'Give me your power') == 3
    assert phrase_search(object, 'Hello world!') == 1
    assert phrase_search(object, 'I wanna nothing') == 0
    assert phrase_search(object, 'Hello again world!') == 0
    assert phrase_search(object, 'I need your clothes, your boots & your motorcycle') == 0

    # my asserts
    assert phrase_search(object, 'i waNNa pizza and pepsi') == 4
    assert phrase_search(object, 'He wants pizza and pepsi') == 5
    assert phrase_search(object, 'I want pizza and pepsi') == 5
    assert phrase_search(object, ' want pizza and pepsi') == 5  # probably set "" in object isn't good idea
    assert phrase_search(object, 'Want pizza and pepsi') == 5
