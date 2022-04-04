#!/usr/bin/python3
'''
Update firmware nrf
'''

import argparse
from enum import Enum
from typing import Optional

from pynrfjprog import HighLevel, LowLevel
from pynrfjprog.Parameters import CoProcessor, DeviceFamily

class Target(Enum):
    """ Enum for NRF programming target """
    NRF91_APP = "NRF91_APP"
    NRF91_MODEM = "NRF91_MODEM"
    NRF52_APP = "NRF52_APP"

    def __str__(self):
        return self.value


def find_target_snr(target: Target, api: HighLevel.API) -> int:
    """ Find the SNR we want to target """
    assert api.is_open(), "API is not open"
    snrs = api.get_connected_probes()
    chosen_snr: Optional[int] = None
    for snr in snrs:
        probe = HighLevel.DebugProbe(api, snr)
        dev_info = probe.get_device_info()
        if (target in [Target.NRF91_APP, Target.NRF91_MODEM] and
                dev_info.device_family == DeviceFamily.NRF91):
            assert chosen_snr is None, "Multiple NRF91 processors connected!"
            chosen_snr = snr
        elif target in [Target.NRF52_APP] and dev_info.device_family == DeviceFamily.NRF52:
            assert chosen_snr is None, "Multiple NRF52 processors connected!"
            chosen_snr = snr

    assert chosen_snr is not None, f"No SNR matching target {target} found!"
    return chosen_snr


def program_nrf91(snr: int, filepath: str, modem_fw: bool):
    """ Program the nrf91 application or modem """
    api = HighLevel.API()
    api.open()
    if modem_fw:
        probe = HighLevel.IPCDFUProbe(api, snr, CoProcessor.CP_MODEM)
    else:
        probe = HighLevel.DebugProbe(api, snr)

    print("Programming")
    probe.program(filepath)
    print("Programming done")
    if modem_fw:
        # Verification is still only supported by modem firmware
        print("Verifying firmware")
        probe.verify(filepath)
        print("Verification done")

    api.close()


def program_nrf52(snr: int, filepath: str):
    """
    Program the nrf52 application
    The reason for this seperate function from nrf91 is that we need to use LowLevel API.
    """
    with LowLevel.API("NRF52") as api:
        api.connect_to_emu_with_snr(snr)
        print("Programming")
        api.erase_all()
        api.program_file(filepath)
        print("Programming done")
        api.disconnect_from_emu()


def program_proc(target: Target, filepath: str):
    """ Find and then program the target """
    api = HighLevel.API()
    api.open()
    snr = find_target_snr(target, api)
    api.close()

    print(f"Request programming of {snr} ({target}) with {filepath}")
    if target == Target.NRF91_MODEM:
        program_nrf91(snr, filepath, modem_fw=True)
    elif target == Target.NRF91_APP:
        program_nrf91(snr, filepath, modem_fw=False)
    else:
        assert target == Target.NRF52_APP
        program_nrf52(snr, filepath)


def main() -> int:
    """ nrf_py_programmer main function """
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="Choose target device", type=Target, choices=list(Target))
    parser.add_argument("filepath", help="Filepath of bin/hex/zip", type=str)

    args = parser.parse_args()

    if args.target in [Target.NRF52_APP, Target.NRF91_APP]:
        assert args.filepath.endswith(".hex") or args.filepath.endswith(".bin"), \
            "Application targets should point to a .hex or .bin file\n" \
            f"Filepath is: {args.filepath}"
    else:
        assert args.target == Target.NRF91_MODEM
        assert args.filepath.endswith(".zip"), \
            "Modem targets should point to a .zip file\n" \
            f"Filepath is: {args.filepath}"

    program_proc(target=args.target, filepath=args.filepath)

    return 0


if __name__ == "__main__":
    main()
