MAX_CONTEXT_WINDOW = 128000*4


def sort_list2_accordingto_list1(list1,list2,reverse=False):
    # https://stackoverflow.com/questions/9764298/given-parallel-lists-how-can-i-sort-one-while-permuting-rearranging-the-other
    # returns list1, list2 as tuples
    return zip(*sorted(zip(list1, list2),reverse=reverse))