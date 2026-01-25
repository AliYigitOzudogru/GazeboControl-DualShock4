# Rover Simulation with PS4 Controller - Complete Setup Guide

## Overview
Complete ROS 2 + Gazebo simulation stack for a 4-wheeled rover with racing-style PS4 DualShock controller support.

## Features
- ✅ Gazebo Ignition/Sim integration with physics
- ✅ ros2_control with diff_drive_controller
- ✅ Racing-style PS4 controller interface (R2=Gas, L2=Brake, Left Stick=Steering)
- ✅ Real-time odometry and joint state publishing
- ✅ Safety features (deadman switch, watchdog timer)
- ✅ Customizable control parameters

## System Requirements
- ROS 2 Humble/Jazzy
- Gazebo Fortress/Garden/Harmonic
- PS4 DualShock controller
- Ubuntu 22.04+ (recommended)

## Dependencies
Install all required ROS 2 packages:
```bash
sudo apt update
sudo apt install -y \
  ros-${ROS_DISTRO}-ros-gz \
  ros-${ROS_DISTRO}-ros-gz-sim \
  ros-${ROS_DISTRO}-ros-gz-bridge \
  ros-${ROS_DISTRO}-gz-ros2-control \
  ros-${ROS_DISTRO}-ros2-control \
  ros-${ROS_DISTRO}-ros2-controllers \
  ros-${ROS_DISTRO}-diff-drive-controller \
  ros-${ROS_DISTRO}-joint-state-broadcaster \
  ros-${ROS_DISTRO}-controller-manager \
  ros-${ROS_DISTRO}-joy \
  ros-${ROS_DISTRO}-xacro \
  ros-${ROS_DISTRO}-robot-state-publisher
```

## PS4 Controller Setup

### 1. Connect Controller
**Bluetooth (Recommended):**
```bash
# Put controller in pairing mode (hold Share + PS button until light bar flashes)
bluetoothctl
> scan on
> pair <CONTROLLER_MAC>
> connect <CONTROLLER_MAC>
> trust <CONTROLLER_MAC>
> exit
```

**USB Cable:**
Simply plug in the controller via USB.

### 2. Test Controller
```bash
# Install jstest if not available
sudo apt install joystick

# Test controller input
jstest /dev/input/js0

# Or use ROS 2 joy node
ros2 run joy joy_node
ros2 topic echo /joy
```

### 3. Verify Axis Mapping
Default PS4 mapping:
- **Axis 0**: Left Stick Horizontal (Steering)
- **Axis 1**: left Stick Vertical
- **Axis 4**: L2 Trigger (Brake/Reverse)
- **Axis 5**: R2 Trigger (Accelerator)
- **Button 0**: X (Deadman Switch)

If your mapping differs, adjust parameters in launch file.

## Build Instructions

```bash
# Navigate to workspace root
cd ~/Desktop/tunay_sonurdf

# Source ROS 2
source /opt/ros/${ROS_DISTRO}/setup.bash

# Build the package
colcon build --packages-select "rover_sim"

# Source the workspace
source install/setup.bash
```

## Launch the Simulation

### Full Simulation Stack
```bash
# Source workspace
source install/setup.bash

# Launch everything
ros2 launch "rover_sim" simulation.launch.py
```

This launches:
1. Gazebo with custom world
2. Rover model spawn
3. ros2_control controllers
4. Joy node (PS4 driver)
5. Custom PS4 drive node
6. ROS-Gazebo bridges

### Launch with Custom Parameters
```bash
ros2 launch "rover_sim" simulation.launch.py \
  world:=/path/to/custom_world.sdf \
  use_sim_time:=true
```

## Control the Rover

### Racing-Style Controls
1. **Hold X Button** (Deadman Switch) - Required for safety
2. **Press R2 Trigger** - Accelerate forward
3. **Press L2 Trigger** - Brake or reverse
4. **Move Left Stick Left/Right** - Steer

### Control Parameters
Adjust in [launch/simulation.launch.py](launch/simulation.launch.py):
- `max_linear_velocity`: Maximum forward/backward speed (m/s)
- `max_angular_velocity`: Maximum turning rate (rad/s)
- `deadman_button`: Button index for safety switch
- `enable_deadman`: Enable/disable deadman requirement
- `steering_sensitivity`: Steering multiplier (0.5-2.0)
- `exponential_steering`: Apply exponential curve for finer control

## File Structure
```
rover_sim/
├── CMakeLists.txt              # ROS 2 build configuration
├── package.xml                 # Package dependencies
├── README.md                   # This file
├── config/
│   ├── controllers.yaml        # ros2_control configuration
│   └── joint_names_rover_sim.yaml
├── launch/
│   ├── simulation.launch.py   # Master launch file (NEW)
│   ├── display.launch          # RViz only (original)
│   └── gazebo.launch           # Gazebo only (original)
├── meshes/                     # 3D models (STL files)
├── scripts/
│   └── ps4_drive_node.py      # Custom PS4 controller node (NEW)
├── textures/                   # Material textures
├── urdf/
│   ├── rover.urdf.xacro       # Modified URDF with Gazebo tags (NEW)
│   └── rover_sim.urdf # Original URDF
└── worlds/
    └── rover_world.sdf        # Gazebo world file (NEW)
```

## Troubleshooting

### Controller Not Detected
```bash
# Check if controller is connected
ls /dev/input/js*

# Check permissions
sudo chmod a+rw /dev/input/js0

# Add user to input group (logout required)
sudo usermod -a -G input $USER
```

### No Movement in Simulation
```bash
# Check if controllers are loaded
ros2 control list_controllers

# Check joy messages
ros2 topic echo /joy

# Check velocity commands
ros2 topic echo /diff_drive_controller/cmd_vel_unstamped

# Verify deadman switch is held (X button)
```

### Gazebo Doesn't Start
```bash
# Check Gazebo installation
gz sim --version

# Try launching Gazebo separately
gz sim -r -v4 worlds/rover_world.sdf
```

### Controllers Fail to Load
```bash
# Check controller manager
ros2 control list_hardware_interfaces

# Manually spawn controllers
ros2 run controller_manager spawner joint_state_broadcaster
ros2 run controller_manager spawner diff_drive_controller
```

### Robot Falls Through Ground
- Ensure collision meshes are properly defined
- Check that `wheel_radius` in controllers.yaml matches actual wheel size
- Verify ground plane has proper friction

## Advanced Configuration

### Tuning Wheel Parameters
Edit [config/controllers.yaml](config/controllers.yaml):
```yaml
diff_drive_controller:
  ros__parameters:
    wheel_separation: 0.51    # Distance between left/right wheels
    wheel_radius: 0.1         # Radius of wheels
```

Measure your rover:
1. Wheel radius: Measure from center to outer edge
2. Wheel separation: Measure from center of left wheel to center of right wheel

### Custom Controller Mapping
If your PS4 controller has different axis mappings, update in launch file:
```python
parameters=[{
    'steering_axis': 0,      # Change if needed
    'accelerator_axis': 5,   # Change if needed
    'brake_axis': 4,         # Change if needed
    'deadman_button': 0,     # Change if needed
}]
```

### Performance Tuning
Edit [config/controllers.yaml](config/controllers.yaml):
```yaml
controller_manager:
  ros__parameters:
    update_rate: 50  # Increase to 100 for faster response

diff_drive_controller:
  ros__parameters:
    linear.x.max_velocity: 2.0      # Adjust max speed
    linear.x.max_acceleration: 1.5   # Adjust acceleration
    angular.z.max_velocity: 3.0      # Adjust turning speed
```

## Monitoring and Debugging

### View Topics
```bash
# List all topics
ros2 topic list

# Monitor key topics
ros2 topic echo /joint_states
ros2 topic echo /odom
ros2 topic echo /diff_drive_controller/cmd_vel_unstamped
```

### View TF Tree
```bash
# Install if needed
sudo apt install ros-${ROS_DISTRO}-tf2-tools

# View transforms
ros2 run tf2_tools view_frames
evince frames.pdf
```

### RViz Visualization
```bash
# Launch RViz separately
rviz2

# Add displays:
# - RobotModel (topic: /robot_description)
# - TF
# - Odometry (topic: /odom)
```

## Known Issues & Limitations
1. Suspension joints are passive (not actuated)
2. Mesh collision may be computationally expensive
3. Controller mapping varies by driver version
4. Trigger normalization depends on joy driver

## References
- [ROS 2 Documentation](https://docs.ros.org/en/humble/)
- [Gazebo Documentation](https://gazebosim.org/)
- [ros2_control Documentation](https://control.ros.org/)
- [diff_drive_controller Documentation](https://control.ros.org/master/doc/ros2_controllers/diff_drive_controller/doc/userdoc.html)

## License
Apache 2.0

## Support
For issues, please check:
1. All dependencies installed correctly
2. Controller properly connected and detected
3. ROS 2 workspace sourced
4. Gazebo and ros2_control running

---
**Created for ROS 2 Humble/Jazzy with Gazebo Ignition/Sim**
# GazeboControl-DualShock4
