# test_wasd_win.py — Windows-only. Robust CARLA connect + WASD/Arrow drive, sync tick, hard-locked chase cam.
# Notes:
#  - No pygame; uses Win32 GetAsyncKeyState.
#  - Works in synchronous mode at 60 FPS fixed delta.
#  - Hard-locked spectator chase camera with fixed height baseline.
#  - Smarter vehicle spawn fallback if Tesla Model 3 isn't in your build.

import sys
import time
import math
import random
import ctypes
import signal

try:
    import carla
except Exception as e:
    print("Failed to import CARLA. Make sure CARLA PythonAPI is in your PYTHONPATH and versions match.")
    print(f"Import error: {e}")
    sys.exit(1)

# ----------- Win32 keyboard (no pygame) -----------
if sys.platform != "win32":
    print("This script uses Win32 GetAsyncKeyState and must run on Windows.")
    sys.exit(0)

user32 = ctypes.windll.user32
GetAsyncKeyState = user32.GetAsyncKeyState

def key_down(vk):  # high bit means down
    return (GetAsyncKeyState(vk) & 0x8000) != 0

# VK codes
VK_ESCAPE = 0x1B
VK_SPACE  = 0x20
VK_LEFT   = 0x25
VK_UP     = 0x26
VK_RIGHT  = 0x27
VK_DOWN   = 0x28

# Letters
K_W = ord('W')   # throttle
K_S = ord('S')   # brake
K_A = ord('A')   # steer left
K_D = ord('D')   # steer right
K_R = ord('R')   # toggle reverse

# Optional aliases (if you like your old keys)
K_E = ord('E')   # throttle alias
K_X = ord('X')   # brake alias

# ----------- Camera settings -----------
CHASE_HEIGHT   = 3.0
CHASE_DISTANCE = 7.5
CHASE_PITCH    = -12.0

def chase_target_transform_fixed(vehicle, dist=CHASE_DISTANCE, z=CHASE_HEIGHT, pitch=CHASE_PITCH, base_z=None):
    tf = vehicle.get_transform()
    yaw_rad = math.radians(tf.rotation.yaw)
    cam_z = base_z if base_z is not None else tf.location.z + z
    loc = carla.Location(
        x=tf.location.x - math.cos(yaw_rad) * dist,
        y=tf.location.y - math.sin(yaw_rad) * dist,
        z=cam_z
    )
    rot = carla.Rotation(pitch=pitch, yaw=tf.rotation.yaw, roll=0.0)
    return carla.Transform(loc, rot)

# ----------- Robust connect helper -----------
def connect_to_carla(host='127.0.0.1', ports=range(2000, 2005), per_try_timeout=2.0, total_wait_s=60):
    """Try multiple ports with retries until a world is available, or raise RuntimeError."""
    start = time.time()
    last_err = None
    while time.time() - start < total_wait_s:
        for port in ports:
            try:
                client = carla.Client(host, port)
                client.set_timeout(per_try_timeout)
                world = client.get_world()   # raises if server not ready
                # quick sanity call to ensure world is responsive
                _ = world.get_map()
                print(f"Connected to CARLA at {host}:{port}")
                return client, world
            except Exception as e:
                last_err = e
        time.sleep(0.5)
    raise RuntimeError(f"Could not connect to CARLA within {total_wait_s}s. Last error: {last_err}")

# ----------- Utility -----------
def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x

# ----------- Main -----------
def main():
    # Allow graceful Ctrl+C even inside CARLA loops
    signal.signal(signal.SIGINT, lambda *args: (_ for _ in ()).throw(KeyboardInterrupt))

    # 1) CONNECT (waits until server is really ready)
    try:
        client, world = connect_to_carla(host='127.0.0.1', ports=range(2000, 2005),
                                         per_try_timeout=2.0, total_wait_s=90)
    except RuntimeError as e:
        print(str(e))
        print("\nTroubleshoot:")
        print(" • Make sure CarlaUE4/UE5 is running and the map is loaded (FPS visible).")
        print(" • Allow Windows Firewall access for CARLA.")
        print(" • Ensure the server port matches (default 2000) and isn’t in use.")
        print(" • Use the same CARLA version for server and PythonAPI.")
        return

    # 2) SYNC MODE
    original_settings = world.get_settings()
    settings = world.get_settings()
    settings.synchronous_mode = True
    settings.fixed_delta_seconds = 1.0 / 60.0
    world.apply_settings(settings)

    # (Optional) sync Traffic Manager
    tm = None
    try:
        tm = client.get_trafficmanager()
        tm.set_synchronous_mode(True)
    except Exception:
        tm = None

    vehicle = None
    try:
        # 3) Spawn vehicle (prefer Tesla; fallback to any 4-wheeled drivable vehicle)
        bp_lib = world.get_blueprint_library()

        def pick_vehicle_blueprint():
            # Try Tesla first
            name = 'vehicle.tesla.model3'
            if any(bp.id == name for bp in bp_lib.filter('vehicle.*')):
                bp = bp_lib.find(name)
                return bp
            # Fallback: filter to typical driveable vehicles (exclude trailers, bikes, etc.)
            candidates = [bp for bp in bp_lib.filter('vehicle.*')
                          if not bp.id.startswith('vehicle.carlamotors.carlacola') and
                             not bp.id.endswith('.bh_crossbike') and
                             not ('microlino' in bp.id)]
            return random.choice(candidates) if candidates else None

        bp = pick_vehicle_blueprint()
        if bp is None:
            raise RuntimeError("No vehicle blueprints available in this map/build.")

        if bp.has_attribute('role_name'):
            bp.set_attribute('role_name', 'hero')
        if bp.has_attribute('color'):
            # visible red for easy spotting
            bp.set_attribute('color', '255,0,0')

        spawn_points = world.get_map().get_spawn_points()
        if not spawn_points:
            raise RuntimeError("No spawn points on this map.")
        random.shuffle(spawn_points)

        for sp in spawn_points:
            vehicle = world.try_spawn_actor(bp, sp)
            if vehicle:
                break
        if vehicle is None:
            raise RuntimeError("Failed to spawn a vehicle (no free spawn points).")

        # Reduce wheel popping if available
        try:
            phys = vehicle.get_physics_control()
            # Some CARLA versions expose this flag; ignore if not present
            if hasattr(phys, "use_sweep_wheel_collision"):
                phys.use_sweep_wheel_collision = True
                vehicle.apply_physics_control(phys)
        except Exception:
            pass

        vehicle.set_autopilot(False)
        spectator = world.get_spectator()

        # Fixed-height chase cam baseline
        spawn_tf = vehicle.get_transform()
        base_cam_z = spawn_tf.location.z + CHASE_HEIGHT
        spectator.set_transform(chase_target_transform_fixed(vehicle, base_z=base_cam_z))

        print("\nManual drive (Windows global hotkeys):")
        print("  W / UpArrow  = throttle     S / DownArrow = brake")
        print("  A / Left     = steer left   D / Right     = steer right")
        print("  Space = handbrake   R = toggle reverse   Esc = quit")
        print("Tip: Steering alone won’t move the car; hold W while steering.\n")

        # 4) Control state
        throttle = 0.0
        steer = 0.0
        reverse = False
        prev_r = False

        # Tunables
        THROTTLE_RISE   = 0.055
        THROTTLE_FALL   = 0.060
        START_BOOST     = 0.22
        BRAKE_FULL      = 1.0
        STEER_STEP      = 0.040
        STEER_DECAY     = 0.90
        STEER_DEADZONE  = 0.02

        # Prime world
        world.tick()

        # Main loop
        while True:
            # Inputs
            if key_down(VK_ESCAPE):
                break

            r_now = key_down(K_R)
            if r_now and not prev_r:
                reverse = not reverse
            prev_r = r_now

            throttle_key = key_down(K_W) or key_down(VK_UP) or key_down(K_E)
            if throttle_key:
                throttle = clamp(throttle + THROTTLE_RISE, 0.0, 1.0)
            else:
                throttle = clamp(throttle - THROTTLE_FALL, 0.0, 1.0)

            brake_key = key_down(K_S) or key_down(VK_DOWN) or key_down(K_X)
            brake = BRAKE_FULL if brake_key else 0.0

            handbrake = key_down(VK_SPACE)

            if key_down(K_A) or key_down(VK_LEFT):
                steer -= STEER_STEP
            elif key_down(K_D) or key_down(VK_RIGHT):
                steer += STEER_STEP
            else:
                steer *= STEER_DECAY
            steer = 0.0 if (-STEER_DEADZONE < steer < STEER_DEADZONE) else clamp(steer, -1.0, 1.0)

            # Start boost to overcome static friction from rest
            vel = vehicle.get_velocity()
            speed = math.sqrt(vel.x * vel.x + vel.y * vel.y + vel.z * vel.z)
            if throttle_key and speed < 0.15 and throttle < START_BOOST and not handbrake and brake == 0.0:
                throttle = START_BOOST

            applied_throttle = 0.0 if (handbrake or brake > 0.0) else throttle

            # Apply control → tick → camera (hard-locked)
            vehicle.apply_control(carla.VehicleControl(
                throttle=applied_throttle,
                steer=steer,
                brake=brake,
                hand_brake=handbrake,
                reverse=reverse
            ))

            # In sync mode, tick drives the sim deterministically at fixed_delta_seconds
            world.tick()

            # Update chase cam after physics step
            spectator.set_transform(chase_target_transform_fixed(vehicle, base_z=base_cam_z))

    except KeyboardInterrupt:
        pass
    finally:
        # Clean up safely
        try:
            if tm:
                tm.set_synchronous_mode(False)
        except Exception:
            pass
        try:
            world.apply_settings(original_settings)
        except Exception:
            pass
        try:
            if vehicle is not None and vehicle.is_alive:
                vehicle.destroy()
        except Exception:
            pass
        print("Closed.")

if __name__ == "__main__":
    main()
