from __future__ import annotations

import math
from threading import RLock
from typing import Any

from reactivex.disposable import Disposable

from dimos.agents.annotation import skill
from dimos.agents.capabilities import CAP_MOVEMENT
from dimos.agents.skills.speak_skill import SpeakSkill
from dimos.core.coordination.blueprints import autoconnect
from dimos.core.coordination.module_coordinator import ModuleCoordinator
from dimos.core.core import rpc
from dimos.core.module import Module, ModuleConfig
from dimos.core.stream import In, Out
from dimos.msgs.geometry_msgs.PoseStamped import PoseStamped
from dimos.msgs.geometry_msgs.Vector3 import Vector3
from dimos.msgs.nav_msgs.Path import Path
from dimos.robot.unitree.go2.blueprints.agentic.unitree_go2_agentic_ollama import (
    unitree_go2_agentic_ollama,
)
from dimos.utils.logging_config import setup_logger

logger = setup_logger()

_TRAIL_ENTITY = "world/breadcrumb/trail"
_HOME_ENTITY = "world/breadcrumb/home"
_TRAIL_COLOR = (255, 140, 0)
_HOME_COLOR = (0, 255, 170)


class BreadcrumbConfig(ModuleConfig):
    spacing_m: float = 0.5


class BreadcrumbRecorder(Module):
    """Records a sparse breadcrumb trail and can send the robot back home.

    The first recorded point is the home anchor. While recording is enabled, the
    module stores a new breadcrumb whenever the robot has moved at least
    ``spacing_m`` meters in the x/y plane from the last stored point.
    """

    config: BreadcrumbConfig

    odom: In[PoseStamped]
    breadcrumb_path: Out[Path]
    goal_request: Out[PoseStamped]

    _lock: RLock
    _recording: bool
    _latest_odom: PoseStamped | None
    _home_pose: PoseStamped | None
    _last_recorded_pose: PoseStamped | None
    _breadcrumbs: list[PoseStamped]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._lock = RLock()
        self._recording = False
        self._latest_odom = None
        self._home_pose = None
        self._last_recorded_pose = None
        self._breadcrumbs = []

    @rpc
    def start(self) -> None:
        super().start()
        self._init_rerun()
        self.register_disposable(Disposable(self.odom.subscribe(self._on_odom)))

    def _on_odom(self, odom: PoseStamped) -> None:
        with self._lock:
            self._latest_odom = odom
            if not self._recording:
                return

            if self._home_pose is None:
                self._append_breadcrumb_locked(odom)
                self._home_pose = self._copy_pose(odom)
                logger.info("Breadcrumb recording anchored home", home=str(self._home_pose))
                return

            if self._last_recorded_pose is None:
                self._append_breadcrumb_locked(odom)
                return

            if self._distance_xy(self._last_recorded_pose, odom) >= self.config.spacing_m:
                self._append_breadcrumb_locked(odom)

    @skill
    def start_breadcrumb_recording(self, spacing_m: float | None = None) -> str:
        """Start recording the robot's walked trail for a future return home.

        Use this when the walk begins. The first odometry point becomes home.

        Args:
            spacing_m: Optional breadcrumb spacing in meters. Good values are 0.5 or 1.0.
        """
        with self._lock:
            if spacing_m is not None:
                if spacing_m <= 0:
                    return "Spacing must be greater than zero."
                self.config.spacing_m = spacing_m

            if self._latest_odom is None:
                return "No odometry yet. Wait for the robot to start publishing position."

            self._recording = True
            self._breadcrumbs = []
            self._home_pose = None
            self._last_recorded_pose = None
            self._append_breadcrumb_locked(self._latest_odom)
            self._home_pose = self._copy_pose(self._latest_odom)

            logger.info(
                "Breadcrumb recording started",
                spacing_m=self.config.spacing_m,
                home=str(self._home_pose),
            )
            return (
                f"Breadcrumb recording started at ({self._home_pose.x:.2f}, {self._home_pose.y:.2f}) "
                f"with spacing {self.config.spacing_m:.2f}m."
            )

    @skill
    def stop_breadcrumb_recording(self) -> str:
        """Stop recording the breadcrumb trail but keep the saved route and home point."""
        with self._lock:
            self._recording = False
            return f"Breadcrumb recording stopped. Stored {len(self._breadcrumbs)} points."

    @skill
    def clear_breadcrumbs(self) -> str:
        """Clear the current breadcrumb trail and forget the saved home position."""
        with self._lock:
            self._recording = False
            self._breadcrumbs = []
            self._home_pose = None
            self._last_recorded_pose = None
            self._publish_path_locked()
            return "Cleared breadcrumbs and home position."

    @skill
    def breadcrumb_status(self) -> str:
        """Report whether breadcrumb tracking is active and where home is."""
        with self._lock:
            home = self._home_pose
            if home is None:
                return (
                    f"Breadcrumb tracking {'is' if self._recording else 'is not'} active. "
                    "No home position has been recorded yet."
                )

            latest = self._latest_odom
            distance = self._distance_xy(latest, home) if latest is not None else 0.0
            return (
                f"Breadcrumb tracking {'is' if self._recording else 'is not'} active. "
                f"Stored {len(self._breadcrumbs)} points. Home is at ({home.x:.2f}, {home.y:.2f}). "
                f"Current distance from home is {distance:.2f}m."
            )

    @skill(uses=[CAP_MOVEMENT])
    def take_me_home(self) -> str:
        """Send the robot to the recorded home position using the navigation planner.

        Use this when the patient says "take me home". The planner computes a
        route from the robot's current position to the first recorded breadcrumb.
        """
        with self._lock:
            if self._home_pose is None:
                return "No home position recorded yet. Start breadcrumb recording first."
            home = self._copy_pose(self._home_pose)

        self.goal_request.publish(home)
        logger.info("Breadcrumb home goal published", home=str(home))
        return (
            f"Heading home via the planner to ({home.x:.2f}, {home.y:.2f}). "
            "The route will be planned from the current costmap."
        )

    def _append_breadcrumb_locked(self, pose: PoseStamped) -> None:
        copied = self._copy_pose(pose)
        self._breadcrumbs.append(copied)
        self._last_recorded_pose = copied
        home_distance = self._distance_xy(copied, self._home_pose) if self._home_pose is not None else 0.0
        logger.info(
            "Breadcrumb remembered",
            index=len(self._breadcrumbs),
            x=round(copied.x, 3),
            y=round(copied.y, 3),
            z=round(copied.z, 3),
            frame_id=copied.frame_id,
            distance_from_home_m=round(home_distance, 3),
        )
        self._publish_path_locked()

    def _publish_path_locked(self) -> None:
        path = Path(
            ts=self._latest_odom.ts if self._latest_odom is not None else None,
            frame_id=self._path_frame_id_locked(),
            poses=list(self._breadcrumbs),
        )
        self.breadcrumb_path.publish(path)
        self._log_rerun_path(path)
        self._log_rerun_home()

    def _path_frame_id_locked(self) -> str:
        if self._breadcrumbs:
            return self._breadcrumbs[0].frame_id
        if self._latest_odom is not None:
            return self._latest_odom.frame_id
        return "world"

    @staticmethod
    def _copy_pose(pose: PoseStamped) -> PoseStamped:
        return PoseStamped(
            ts=pose.ts,
            frame_id=pose.frame_id,
            position=Vector3(pose.x, pose.y, pose.z),
            orientation=pose.orientation,
        )

    @staticmethod
    def _distance_xy(a: PoseStamped, b: PoseStamped) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    @staticmethod
    def _init_rerun() -> None:
        from dimos.visualization.rerun.init import rerun_init

        rerun_init("hackmitdog-breadcrumb")

    def _log_rerun_path(self, path: Path) -> None:
        import rerun as rr

        rr.log(_TRAIL_ENTITY, path.to_rerun(color=_TRAIL_COLOR, z_offset=0.15, radii=0.08))

    def _log_rerun_home(self) -> None:
        import rerun as rr

        if self._home_pose is None:
            rr.log(_HOME_ENTITY, rr.Points3D(positions=[]))
            return

        rr.log(
            _HOME_ENTITY,
            rr.Points3D(
                positions=[[self._home_pose.x, self._home_pose.y, self._home_pose.z + 0.2]],
                colors=[_HOME_COLOR],
                radii=[0.16],
                labels=["home"],
            ),
        )


breadcrumb_agentic_sim = autoconnect(
    unitree_go2_agentic_ollama.disabled_modules(SpeakSkill),
    BreadcrumbRecorder.blueprint(),
).global_config(simulation="mujoco")


if __name__ == "__main__":
    ModuleCoordinator.build(breadcrumb_agentic_sim).loop()