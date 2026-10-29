import os
import io
import tarfile
import shutil
import asyncio
from typing import AsyncGenerator
import docker
from docker.errors import DockerException, NotFound, APIError
from app.config import settings

# Active SSE log stream counters per user: user_id -> count
user_active_streams: dict[str, int] = {}

def get_docker_client() -> docker.DockerClient:
    """Returns official Docker SDK client connected to host socket."""
    return docker.from_env()


class RealDockerService:
    @staticmethod
    def get_bot_network(client: docker.DockerClient, bot_id: str):
        """Creates or retrieves a dedicated isolated bridge network for this bot."""
        net_name = f"bothost_net_{bot_id}"
        try:
            return client.networks.get(net_name)
        except NotFound:
            return client.networks.create(
                net_name,
                driver="bridge",
                internal=False,
                labels={"bothost.bot_id": bot_id},
            )

    @staticmethod
    def get_bot_volume(client: docker.DockerClient, bot_id: str):
        """Creates or retrieves dedicated persistent volume for /data mount."""
        vol_name = f"bothost_data_{bot_id}"
        try:
            return client.volumes.get(vol_name)
        except NotFound:
            return client.volumes.create(
                vol_name,
                labels={"bothost.bot_id": bot_id},
            )

    @staticmethod
    def build_bot_image(bot_id: str, source_dir: str, log_callback=None) -> str:
        """
        Builds Docker image for bot using Docker SDK low-level API,
        streaming build output to log_callback so user sees progress/errors.
        """
        client = get_docker_client()
        image_tag = f"bothost_bot_{bot_id}:latest"

        # Use low-level API build to capture streamed build output
        api_client = client.api
        generator = api_client.build(
            path=source_dir,
            tag=image_tag,
            rm=True,
            forcerm=True,
            decode=True,
        )

        for chunk in generator:
            if "stream" in chunk:
                line = chunk["stream"].strip()
                if line and log_callback:
                    log_callback(f"[Build] {line}")
            elif "error" in chunk:
                err_msg = chunk["error"].strip()
                if log_callback:
                    log_callback(f"[Build Error] {err_msg}")
                raise RuntimeError(f"Docker build failed: {err_msg}")

        return image_tag

    @staticmethod
    def run_bot_container(
        bot_id: str,
        env_vars_dict: dict[str, str],
        source_dir: str,
        log_callback=None,
    ) -> str:
        """
        Runs bot container enforcing all security constraints:
        - memory limit 256 MB, memswap equal (no swap)
        - nano_cpus for 0.25 CPU (250_000_000)
        - pids_limit 100
        - non-root user (10001:10001)
        - read_only root filesystem
        - tmpfs for /tmp (64 MB)
        - cap_drop: ALL, security_opt: no-new-privileges
        - dedicated named volume mounted at /data (rw)
        - env DATA_DIR=/data
        - restart policy: on-failure (max 5)
        - log driver: json-file (5m max-size, 3 max-file)
        - dedicated user-defined bridge network per bot
        """
        client = get_docker_client()

        # 1. Build image if needed
        image_tag = RealDockerService.build_bot_image(bot_id, source_dir, log_callback)

        # 2. Get resources
        network = RealDockerService.get_bot_network(client, bot_id)
        volume = RealDockerService.get_bot_volume(client, bot_id)
        container_name = f"bothost_bot_{bot_id}"

        # 3. Clean any existing container idempotently
        try:
            existing = client.containers.get(container_name)
            existing.remove(force=True)
        except NotFound:
            pass

        # 4. Prepare environment variables
        env_payload = env_vars_dict.copy()
        env_payload["DATA_DIR"] = "/data"

        # 5. Run container with strict constraints
        container = client.containers.run(
            image=image_tag,
            name=container_name,
            detach=True,
            # Security & User
            user="10001:10001",
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            # Resource Limits (Free Tier)
            mem_limit="256m",
            memswap_limit="256m",  # Equal to mem_limit -> Disables swap
            nano_cpus=250000000,   # 0.25 CPU
            pids_limit=100,
            # Storage & Tmpfs
            tmpfs={"/tmp": "rw,size=64m"},
            volumes={
                volume.name: {"bind": "/data", "mode": "rw"},
            },
            # Isolation & Logs
            network=network.name,
            log_config=docker.types.LogConfig(
                type=docker.types.LogConfig.types.JSON,
                config={"max-size": "5m", "max-file": "3"},
            ),
            restart_policy={"Name": "on-failure", "MaximumRetryCount": 5},
            environment=env_payload,
            labels={"bothost.bot_id": bot_id},
        )

        return container.id

    @staticmethod
    def start_bot(bot_id: str) -> bool:
        """Idempotently starts container."""
        client = get_docker_client()
        name = f"bothost_bot_{bot_id}"
        try:
            container = client.containers.get(name)
            if container.status != "running":
                container.start()
            return True
        except NotFound:
            return False

    @staticmethod
    def stop_bot(bot_id: str) -> bool:
        """Idempotently stops container with 10s grace period."""
        client = get_docker_client()
        name = f"bothost_bot_{bot_id}"
        try:
            container = client.containers.get(name)
            if container.status == "running":
                container.stop(timeout=10)
            return True
        except NotFound:
            return False

    @staticmethod
    def restart_bot(bot_id: str) -> bool:
        """Idempotently restarts container."""
        client = get_docker_client()
        name = f"bothost_bot_{bot_id}"
        try:
            container = client.containers.get(name)
            container.restart(timeout=10)
            return True
        except NotFound:
            return False

    @staticmethod
    def delete_bot_resources(bot_id: str, delete_volume: bool = False):
        """
        Idempotently deletes container, image, network, source dir,
        and (if delete_volume=True) the /data volume.
        """
        client = get_docker_client()
        container_name = f"bothost_bot_{bot_id}"
        image_tag = f"bothost_bot_{bot_id}:latest"

        # 1. Remove container
        try:
            c = client.containers.get(container_name)
            c.remove(force=True)
        except (NotFound, APIError):
            pass

        # 2. Remove image
        try:
            client.images.remove(image_tag, force=True)
        except (NotFound, APIError):
            pass

        # 3. Remove network
        try:
            net = client.networks.get(f"bothost_net_{bot_id}")
            net.remove()
        except (NotFound, APIError):
            pass

        # 4. Remove volume only if explicitly requested
        if delete_volume:
            try:
                vol = client.volumes.get(f"bothost_data_{bot_id}")
                vol.remove(force=True)
            except (NotFound, APIError):
                pass

        # 5. Remove source folder on host
        bot_src_dir = os.path.join(settings.BOT_STORAGE_DIR, bot_id)
        shutil.rmtree(bot_src_dir, ignore_errors=True)

    @staticmethod
    def get_logs(bot_id: str, lines: int = 200, secrets_to_redact: list[str] = None) -> list[str]:
        """Fetches last N lines of logs from container, redacting any known secrets."""
        client = get_docker_client()
        name = f"bothost_bot_{bot_id}"
        try:
            container = client.containers.get(name)
            raw = container.logs(tail=lines, stdout=True, stderr=True).decode("utf-8", errors="replace")
            log_lines = raw.splitlines()
        except NotFound:
            return ["Konteyner topilmadi yoki hali ishga tushirilmagan."]
        except Exception as e:
            return [f"Jurnallarni o'qishda xatolik: {e}"]

        if not secrets_to_redact:
            return log_lines

        redacted: list[str] = []
        for l in log_lines:
            line_str = l
            for secret in secrets_to_redact:
                if secret and len(secret) >= 4 and secret in line_str:
                    line_str = line_str.replace(secret, "[REDACTED_SECRET]")
            redacted.append(line_str)
        return redacted

    @staticmethod
    def get_container_real_status(bot_id: str) -> str:
        """Reconciles with real Docker container status."""
        client = get_docker_client()
        name = f"bothost_bot_{bot_id}"
        try:
            container = client.containers.get(name)
            c_status = container.status.lower()
            if c_status == "running":
                return "running"
            elif c_status in ["exited", "dead"]:
                exit_code = container.attrs.get("State", {}).get("ExitCode", 0)
                return "stopped" if exit_code == 0 else "crashed"
            return c_status
        except NotFound:
            return "stopped"
        except Exception:
            return "stopped"

    @staticmethod
    def export_data_volume_tar(bot_id: str) -> io.BytesIO:
        """
        Creates a tar.gz stream of the bot's /data volume without stopping the bot
        using a short-lived helper container.
        """
        client = get_docker_client()
        vol_name = f"bothost_data_{bot_id}"

        # Helper container that tars /data to stdout
        output_stream = client.containers.run(
            image="alpine:3.20",
            command=["tar", "czf", "-", "-C", "/data", "."],
            volumes={vol_name: {"bind": "/data", "mode": "ro"}},
            remove=True,
            stdout=True,
            stderr=False,
        )

        buffer = io.BytesIO(output_stream)
        buffer.seek(0)
        return buffer
