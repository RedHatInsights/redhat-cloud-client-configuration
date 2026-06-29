#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-or-later
#
# systemd ExecCondition helper for redhat-cloud-client-configuration (CCT-2110).
# Exit 0  — consumer is suitable for mTLS-backed services (run ExecStart).
# Exit 75 — skip ExecStart (anonymous owner for this consumer); unit succeeds.
# Other   — configuration error; unit fails.
#
# Uses ``busctl call ... GetOrg`` (com.redhat.RHSM1.Consumer) for the current
# owner JSON (same data subscription-manager exposes). Missing cert, D-Bus
# errors, or unreadable owner JSON return 75 so the ExecCondition is considered
# failed and systemd skips the remainder of the unit without marking the unit
# as failed(see systemd.service ExecCondition=).

import json
import os
import subprocess
import sys
from typing import Any, Dict, Optional

# systemd.exec(5): "If the ExecCondition= exits with 75, the job is considered
# successful but skipped"
_SYSTEMD_SKIP_UNIT = 75

_CERT = "/etc/pki/consumer/cert.pem"

# Current owner JSON from subscription-manager (same as:
#   busctl call --json=short com.redhat.RHSM1 \
#    /com/redhat/RHSM1/Consumer \
#     com.redhat.RHSM1.Consumer GetOrg s ""
_GET_ORG_BUSCTL = (
    "busctl",
    "call",
    "--json=short",
    "com.redhat.RHSM1",
    "/com/redhat/RHSM1/Consumer",
    "com.redhat.RHSM1.Consumer",
    "GetOrg",
    "s",
    "",
)


def _parse_busctl_output(busctl_out: str) -> Optional[str]:
    """Decode the output of the busctl call."""
    
    try:
        response = json.loads(busctl_out)
        data = response.get('data')[0]
        data = data[0]
        org_info = json.loads(data)
    except:
        # If parsing fails for any reason assume we don't have owner info
        return None
    
    return org_info

def _owner_dict_from_rhsm_dbus() -> Optional[Dict[str, Any]]:
    """
    Return the current owner dict via ``busctl call`` to Consumer.GetOrg.

    Invokes:
    ``busctl call --json=short com.redhat.RHSM1 /com/redhat/RHSM1/Consumer
    com.redhat.RHSM1.Consumer GetOrg s ""``

    GetOrg returns a JSON string of the owner record (including ``anonymous``).
    Returns None if the call fails, the payload is not a JSON object, or the
    response cannot be parsed.
    """
    try:
        proc = subprocess.run(
            list(_GET_ORG_BUSCTL),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout:
        return None
    return _parse_busctl_output(proc.stdout)


def main() -> int:
    # No consumer cert: not in a state we gate on; ExecCondition succeeds (0).
    if not os.path.isfile(_CERT):
        return _SYSTEMD_SKIP_UNIT
    owner = _owner_dict_from_rhsm_dbus()
    if owner is None:
        return _SYSTEMD_SKIP_UNIT
    if owner.get("anonymous") is True:
        return _SYSTEMD_SKIP_UNIT
    return 0


if __name__ == "__main__":
    sys.exit(main())
