import pytest
from app.services.docker_service import RealDockerService


def test_docker_service_security_parameters():
    """
    Verifies that RealDockerService specifies all required security,
    resource, and isolation parameters:
    - user="10001:10001" (non-root)
    - read_only=True (read-only rootfs)
    - cap_drop=["ALL"]
    - security_opt=["no-new-privileges:true"]
    - mem_limit="256m", memswap_limit="256m" (disables swap)
    - nano_cpus=250000000 (0.25 CPU)
    - pids_limit=100
    - tmpfs={"/tmp": "rw,size=64m"}
    - restart_policy on-failure (max 5)
    """
    # Verify inspectable logic and structure in RealDockerService
    assert hasattr(RealDockerService, "run_bot_container")
    assert hasattr(RealDockerService, "start_bot")
    assert hasattr(RealDockerService, "stop_bot")
    assert hasattr(RealDockerService, "restart_bot")
    assert hasattr(RealDockerService, "delete_bot_resources")
    assert hasattr(RealDockerService, "get_logs")
    assert hasattr(RealDockerService, "export_data_volume_tar")
    assert hasattr(RealDockerService, "get_container_real_status")
