# Copyright (c) 2020 SmarAct GmbH

# Programming example for the SmarPod Python API.
# This example demonstrates how to use the ConfigureSystem command.

# THIS  SOFTWARE, DOCUMENTS, FILES AND INFORMATION ARE PROVIDED 'AS IS'
# WITHOUT WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING,
# BUT  NOT  LIMITED  TO,  THE  IMPLIED  WARRANTIES  OF MERCHANTABILITY,
# FITNESS FOR A PURPOSE, OR THE WARRANTY OF NON-INFRINGEMENT.
# THE  ENTIRE  RISK  ARISING OUT OF USE OR PERFORMANCE OF THIS SOFTWARE
# REMAINS WITH YOU.
# IN  NO  EVENT  SHALL  THE  SMARACT  GMBH  BE  LIABLE  FOR ANY DIRECT,
# INDIRECT, SPECIAL, INCIDENTAL, CONSEQUENTIAL OR OTHER DAMAGES ARISING
# OUT OF THE USE OR INABILITY TO USE THIS SOFTWARE.
#
# WHEN RUNNING, THIS PROGRAMMING EXAMPLE WILL MOVE THE POSITIONER.
# ENSURE THAT THIS CAN'T CAUSE COLLISIONS. THE POSITIONER MUST HAVE
# SUFFICIENT SPACE TO MOVE OVER ITS FULL RANGE.


"""One-time vendor controller configuration followed by sensor calibration.

This writes non-volatile controller memory. It is not a routine startup step;
consult the vendor procedure after firmware, controller or positioner changes.
"""


def main():
    import smaract.smarpod as smarpod

    from smarpod_pcle.config import get_settings
    from smarpod_pcle.hardware import check_lib_compatibility, shutdown

    settings = get_settings().robot
    check_lib_compatibility()
    h = None
    try:
        smarpod.ConfigureController(settings.model, settings.locator)
        print(f"Configured {settings.locator} for SmarPod model {settings.model}")
        h = smarpod.Open(settings.model, settings.locator)
        print("Calibrating sensors...")
        smarpod.Calibrate(h)
    finally:
        shutdown(h)
    print("Controller configured and calibrated.")


if __name__ == "__main__":
    main()
