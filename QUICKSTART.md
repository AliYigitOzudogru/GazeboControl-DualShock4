# Quick Start Guide - PS4 Rover Control

## 🚀 Fast Setup (5 Minutes)

### 1. Install Dependencies (One-time)
```bash
sudo apt install -y ros-${ROS_DISTRO}-ros-gz ros-${ROS_DISTRO}-ros2-controllers \
  ros-${ROS_DISTRO}-gz-ros2-control ros-${ROS_DISTRO}-joy ros-${ROS_DISTRO}-xacro
```

### 2. Build Package
```bash
cd ~/Desktop/tunay_sonurdf
source /opt/ros/${ROS_DISTRO}/setup.bash
colcon build --packages-select "rover_sim"
source install/setup.bash
```

### 3. Connect PS4 Controller
**Bluetooth:** Hold Share + PS button until light flashes
**USB:** Just plug it in

Test:
```bash
ls /dev/input/js0  # Should exist
jstest /dev/input/js0  # Optional test
```

### 4. Launch Simulation
```bash
ros2 launch "rover_sim" simulation.launch.py
```

### 5. Drive!
- **HOLD X BUTTON** (Deadman switch - REQUIRED!)
- **R2 Trigger** = Gas (Forward)
- **L2 Trigger** = Brake/Reverse
- **Left Stick Left/Right** = Steering

---

## 🎮 Controller Layout

```
         L2 Trigger              R2 Trigger
        [BRAKE/REV]             [ACCELERATE]
            
    ┌─────────────────────────────────┐
    │                                 │
    │  Left Stick         Right Stick│
    │  [STEERING]              [N/A] │
    │      │                          │
    │   ───┼───                       │
    │      │                          │
    │                                 │
    │    [Options]       [Menu]       │
    │                                 │
    │  △                          X O │
    │ □ X ← [HOLD X TO DRIVE!]       │
    │  ○                          △ □ │
    └─────────────────────────────────┘
```

---

## 🔧 Common Issues

### "No controller detected"
```bash
sudo chmod 666 /dev/input/js0
```

### "Rover doesn't move"
- Are you holding the X button?
- Check: `ros2 topic echo /joy` - do you see data?
- Check: `ros2 control list_controllers` - are controllers active?

### "Simulation is slow"
Edit `config/controllers.yaml` → reduce `update_rate` to 30

### "Steering is too sensitive"
Edit `launch/simulation.launch.py` → change `steering_sensitivity` to 0.5

---

## 📊 Useful Commands

```bash
# Check if simulation is running
ros2 topic list

# Monitor speed commands
ros2 topic echo /diff_drive_controller/cmd_vel_unstamped

# View robot position
ros2 topic echo /odom

# Check controller status
ros2 control list_controllers

# Kill everything
Ctrl+C (in launch terminal)
```

---

## ⚙️ Quick Tweaks

### Make it faster:
Edit `config/controllers.yaml`:
```yaml
linear.x.max_velocity: 5.0  # Default is 2.0
```

### Disable deadman switch:
Edit `launch/simulation.launch.py`:
```python
'enable_deadman': False,  # Change from True
```

### Change deadman button:
```python
'deadman_button': 3,  # 0=X, 1=O, 2=△, 3=□
```

---

## 📁 Key Files to Edit

| What to Change | Edit This File |
|---------------|----------------|
| Speed/turning limits | `config/controllers.yaml` |
| Controller buttons | `launch/simulation.launch.py` |
| Robot physics | `urdf/rover.urdf.xacro` |
| World environment | `worlds/rover_world.sdf` |

---

## 🆘 Emergency Stop
**Press Ctrl+C in the terminal** or **release the X button**

---

**Ready to drive? Launch and hold X!** 🏁
