def calibration(calib_file, force_units, torque_units):
    """
    Imports
    """
    import xml.etree.ElementTree as ET
    from time import sleep
    import numpy as np
    from GUI.utils import auxilaryfunctions

    """
    load XML file
    """
    tree = ET.parse(calib_file)
    root = tree.getroot()

    num_gages = root.attrib["NumGages"]
    calib_forceUnits = root[0].attrib["ForceUnits"]
    calib_torqueUnits = root[0].attrib["TorqueUnits"]
    if force_units == "None":
        force_units = calib_forceUnits
    if torque_units == "None":
        torque_units = calib_torqueUnits
    print("calib_forceUnits: ", calib_forceUnits, type(calib_forceUnits),
          "calib_torqueUnits: ", calib_torqueUnits)

    # read in calibration matrix:
    calib_matrix_dict = {}
    for nr in range(int(num_gages)):
        string = root[0][nr].attrib["values"]
        values = string.split()
        calib_matrix_dict[root[0][nr].attrib["Name"]] = values
    print("{" + "\n".join("{!r}: {!r},".format(k, v) for k, v in calib_matrix_dict.items()) + "}")

    sleep(0.01)
    # convert dict entries into array matrix format:
    calib_matrix = []
    for k,v in calib_matrix_dict.items():
        calib_matrix.append(v)
    calib_matrix = np.array(calib_matrix)
    calibration_matrix = auxilaryfunctions.convert_all_elem_in_2darray(calib_matrix, float)  # Matrix A
    print("calibration matrix: \n", calibration_matrix, "\nshape: ", calibration_matrix.shape)

    # check if units from calib differ from user input, if so calibrate accordingly.
    if calib_forceUnits != force_units:
        # calib_forceUnits should be N
        # TODO: calibrate
        print("force calibration required")

    if calib_torqueUnits != torque_units:
        print("torque calibration required")
        # calib_torqueUnits should be N-mm
        if torque_units == "N-m":
            # divide torque values by 1000:
            convert_to_Nm = np.array([[1.0, 1.0, 1.0, 0.001, 0.001, 0.001],
                               [1.0, 1.0, 1.0, 0.001, 0.001, 0.001],
                               [1.0, 1.0, 1.0, 0.001, 0.001, 0.001],
                               [1.0, 1.0, 1.0, 0.001, 0.001, 0.001],
                               [1.0, 1.0, 1.0, 0.001, 0.001, 0.001],
                               [1.0, 1.0, 1.0, 0.001, 0.001, 0.001]])

            print("convert_to_Nm array: \n", convert_to_Nm)     # Matrix B
            calib_matrix_Nm = calib_matrix*convert_to_Nm
            print("calibrated Matrix: ", calib_matrix_Nm)

            calibration_matrix = calib_matrix_Nm
    return calibration_matrix, force_units, torque_units, num_gages