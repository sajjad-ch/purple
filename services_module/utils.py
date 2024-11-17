import random


def random_code():
    number_list = [x for x in range(10)]
    code = []
    for i in range(8):
        num = random.choice(number_list)
        code.append(num)

    code_string = "".join(str(item) for item in code)
    return code_string
