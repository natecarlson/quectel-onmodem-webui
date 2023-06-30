import time
import re
import logging
from ..command import Command, ResultValue, ResultValueState
from .helper_functions import decode_nr5g_bandwidth, decode_lte_bandwidth

logger = logging.getLogger(__name__)

class CarrierAggregationCommand(Command):
    """
    Checks Serving Cell information
    """

    def __init__(self):
        super().__init__("QCAINFO", "Carrier Aggregation Information")

    def poll(self, serial_port):

        # Send the Serving Cell query
        logger.debug("Polling QCAINFO...")
        serial_port.write("AT+QCAINFO\r\n".encode("utf-8"))

        # Wait for the response to be written
        time.sleep(0.5)

        # Read the response content
        cmd_result = self.receive(serial_port, multi_result=True)

        # Clear the results
        self.results = []

        if not cmd_result[0]:
            logger.warn("No response to QCAINFO query")
            # No results to work with
            return

        """
        Example response:
        at+qcainfo
        +QCAINFO: "PCC",66786,100,"LTE BAND 66",1,40,-103,-15,-69,-1
        +QCAINFO: "SCC",520110,12,"NR5G BAND 41",7
        """

        """
        Response meanings:

        LTE-only:
        +QCAINFO: "PCC",<earfcn>,<bandwidth>,<band>,<pcell_state>,<PCID>,<RSRP>,<RSRQ>,<RSSI>,<RSSNR>
        [+QCAINFO: "SCC",<earfcn>,<bandwidth>,<band>,<scell_state>,<PCID>,<RSRP>,<RSRQ>,<RSSI>,<RSSNR>,<UL_configured>,<UL_bandwidth>,<UL_EARFCN>]

        5G NSA:
        +QCAINFO: "PCC",<earfcn>,<bandwidth>,<band>,<pcell_state>,<PCID>,<RSRP>,<RSRQ>,<RSSI>,<RSSNR>
        [+QCAINFO: "SCC",<earfcn>,<bandwidth>,<band>,<scell_state>,<PCID>,<RSRP>,<RSRQ>,<RSSI>,<RSSNR>,<UL_configured>,<UL_bandwidth>,<UL_EARFCN>]
        [+QCAINFO: "SCC",<earfcn>,<NR_DL_bandwidth>,<NR_band>,<PCID>]
        [+QCAINFO: "SCC",<earfcn>,<NR_DL_bandwidth>,<NR_band>,<state>,<PCID>,<UL_configured>,<NR_UL_bandwidth>,<UL_ARFCN>]

        5G SA:
        +QCAINFO: "PCC",<earfcn>,<NR_DL_bandwidth>,<NR_band>,<PCID>
        [+QCAINFO: "SCC",<earfcn>,<NR_DL_bandwidth>,<NR_band>,<state>,<PCID>,<UL_configured>,<NR_UL_bandwidth>,<UL_ARFCN>]

        I believe it returns OK if no carrier aggregation is present, could be error though. Need to test.

        This command does not identify NR5G vs NR5G-SA.
        """

        logging.debug(f"QCAINFO response: {cmd_result[1]}")

        for result_line in cmd_result[1]:

            if result_line.startswith("AT"):
                continue
            elif result_line.startswith("OK"):
                continue
            elif result_line.startswith("ERROR"):
                logging.warn("QCAINFO returned ERROR, not sure if that's OK.")
                continue

            #qcainfo_matches  = re.match(r'\+QCAINFO:\s"([A-Z]+)",([0-9])+,([0-9]+),"(.* BAND [0-9]+)"(,.*+)?', result_line)
            qcainfo_matches = re.match(r'\+QCAINFO:\s"([A-Z]+)",([0-9]+),([0-9]+),"(.* BAND [0-9]+)",(.*)', result_line)

            """
            1st matchgroup: PCC or SCC
            2nd matchgroup: EARFCN
            3rd matchgroup: Bandwidth
            4th matchgroup: Band (prefixed with LTE BAND or NR5G BAND)

            If LTE band:
            5th matchgroup: PCell state
            6th matchgroup: PCID
            7th matchgroup: RSRP
            8th matchgroup: RSRQ
            9th matchgroup: RSSI
            10th matchgroup: RSSNR
            Optionally:
            11th matchgroup: UL configured -- this will equal 0 or 1.
            12th matchgroup: UL bandwidth -- this will be - if UL configured is 0.
            13th matchgroup: UL EARFCN -- this will be - if UL configured is 0.

            If 5G NSA band, PCC:
            5th matchgroup: PCID

            If 5G NSA band, SCC:
            5th matchgroup: state
            6th matchgroup: PCID
            7th matchgroup: UL configured
            8th matchgroup: UL bandwidth
            9th matchgroup: UL ARFCN

            """

            logging.debug(f"qcainfo_matches: {qcainfo_matches.groups()}")

            # Set things that are common to each type
            if qcainfo_matches is not None:
                conntype = qcainfo_matches.group(1)
                earfcn = qcainfo_matches.group(2)
                bandwidth = qcainfo_matches.group(3)
                band = qcainfo_matches.group(4)

                if band.startswith("LTE BAND"):
                    technology = "LTE"
                    decoded_bandwidth = decode_lte_bandwidth(bandwidth)
                elif band.startswith("NR5G BAND"):
                    # Not possible to differentiate between SA and NSA from the QCAINFO alone.
                    technology = "5GNR"
                    decoded_bandwidth = decode_nr5g_bandwidth(bandwidth)
                else:
                    logging.warning(f"Unknown technology in band: {band}")
                    technology = "Unknown"

                self.results.append(ResultValue(f"{technology}_conntype", f"{technology} Connection Type", "PCC is primary, SCC is seconday", conntype))
                self.results.append(ResultValue(f"{technology}_earfcn", f"{technology} EARFCN", "E-UTRA Absolute Radio Frequency Channel Number", earfcn))
                self.results.append(ResultValue(f"{technology}_bandwidth", f"{technology} Bandwidth", "Bandwidth", decoded_bandwidth))
                self.results.append(ResultValue(f"{technology}_band", f"{technology} Band", "Band tech and number", band))

            if len(qcainfo_matches.groups()) >= 5:
                qca_params = qcainfo_matches.group(5).split(",")
            else:
                qca_params = [qcainfo_matches[5]]

            if len(qca_params) >= 6:
                # LTE
                self.results.append(ResultValue("lte_pcell_state", "LTE PCell State", "LTE PCell State", qca_params[0]))
                self.results.append(ResultValue("lte_pcid", "LTE PCID", "Physical Cell ID", qca_params[1]))
                self.results.append(ResultValue("lte_rsrp", "LTE RSRP", "Reference Signal Received Power", qca_params[2]))
                self.results.append(ResultValue("lte_rsrq", "LTE RSRQ", "Reference Signal Received Quality", qca_params[3]))
                self.results.append(ResultValue("lte_rssi", "LTE RSSI", "Reference Signal Strength Indicator", qca_params[4]))
                self.results.append(ResultValue("lte_rssnr", "LTE RSSNR", "Reference Signal Signal to Noise Ratio", qca_params[5]))
                if len(qca_params) >= 9:
                    self.results.append(ResultValue("lte_ul_configured", "LTE UL Configured", "Is upload configured?", qca_params[6]))
                    self.results.append(ResultValue("lte_ul_bandwidth", "LTE UL Bandwidth", "Upload bandwidth", decode_lte_bandwidth(qca_params[7])))
                    self.results.append(ResultValue("lte_ul_earfcn", "LTE UL EARFCN", "EARFCN", qca_params[8]))

            elif len(qca_params) >= 2:
                self.results.append(ResultValue("5gnr_cell_state", "5G Cell State", "5G Cell State", qca_params[0]))
                self.results.append(ResultValue("5gnr_pcid", "5G PCID", "Physical Cell ID", qca_params[1]))
                if len(qca_params) >= 5:
                    self.results.append(ResultValue("5gnr_ul_configured", "UL Configured", "Is upload configured?", qca_params[2]))
                    self.results.append(ResultValue("5gnr_ul_bandwidth", "UL Bandwidth", "Upload bandwidth", decode_nr5g_bandwidth(qca_params[3])))
                    self.results.append(ResultValue("5gnr_ul_arfcn", "UL ARFCN", "ARFCN", qca_params[4]))


            elif len(qca_params) >= 1:
                self.results.append(ResultValue("5gnr_pcid", "5G PCID", "Physical Cell ID", qca_params[0]))

            else:
                logging.warning(f"Line does not match as expected. Line: {result_line}")
                continue

        self.last_update = time.time()
