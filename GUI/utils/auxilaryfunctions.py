def convert_all_elem_in_2darray(array, new_type=float):
    """converts all elements in array to new type, default float"""
    import numpy as np

    conv_array = array.astype(new_type)
    return conv_array