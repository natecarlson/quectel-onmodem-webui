import logging

logger = logging.getLogger(__name__)

def decode_nr5g_bandwidth(coded_bandwidth):
    coded_bandwidth = int(coded_bandwidth)

    nr5g_bandwidth = {
        0: "5MHz",
        1: "10MHz",
        2: "15MHz",
        3: "20MHz",
        4: "25MHz",
        5: "30MHz",
        6: "40MHz",
        7: "50MHz",
        8: "60MHz",
        9: "70MHz",
        10: "80MHz",
        11: "90MHz",
        12: "100MHz",
        13: "200MHz",
        14: "400MHz",
    }

    if coded_bandwidth in nr5g_bandwidth:
        return nr5g_bandwidth[coded_bandwidth]

    else:
        logger.warning(f"Unknown NR5G bandwidth; type: {type(coded_bandwidth)}, val: {coded_bandwidth}")
        return f"Unknown NR5G bandwidth; type: {type(coded_bandwidth)}, val: {coded_bandwidth})"


def decode_lte_bandwidth(coded_bandwidth):
    coded_bandwidth = int(coded_bandwidth)

    # This is rougly coded_bandwidth * 0.2 = bandwidth in MHz, but not for '6'.
    # This weirdly is different in the definition between servingcell and qcainfo, but does not overlap.
    lte_bandwidth = {
        0: "1.4 MHz",
        1: "3 MHz",
        2: "5 MHz",
        3: "10 MHz",
        4: "15 MHz",
        5: "20 MHz",
        6: '1.4 MHz',
        15: '3 MHz',
        25: '5 MHz',
        50: '10 MHz',
        75: '15 MHz',
        100: '20 MHz',
    }

    if coded_bandwidth in lte_bandwidth:
        return lte_bandwidth[coded_bandwidth]

    else:
        logger.warning(f"Unknown LTE bandwidth; type: {type(coded_bandwidth)}, val: {coded_bandwidth}")
        return f"Unknown LTE bandwidth; type: {type(coded_bandwidth)}, val: {coded_bandwidth})"
