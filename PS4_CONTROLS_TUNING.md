# PS4 Arcade-Style Rover Control - Tuning Guide

## Overview
The rover control system has been optimized for **GTA5-style arcade driving** with your PS4 DualShock4 controller. This guide helps you fine-tune the feel to match your preferences.

## Current Presets (Optimized for Arcade Driving)

### Sensitivity Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `steering_sensitivity` | 1.2 | 0.5-2.0 | **How responsive steering is** (↑ = sharper turns) |
| `steering_power` | 1.5 | 1.0-2.5 | Exponential curve shape (↓ = more linear, ↑ = more sensitive at edges) |
| `deadzone` | 0.1 | 0.0-0.3 | Joystick dead zone size (↓ = more sensitive) |
| `trigger_deadzone` | 0.02 | 0.01-0.1 | Accelerator/brake sensitivity (↓ = more sensitive) |

### Acceleration Tuning

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `max_linear_velocity` | 2.5 | 1.0-4.0 | **Maximum rover speed (m/s)** |
| `max_angular_velocity` | 4.5 | 2.0-7.0 | **Maximum turning speed (rad/s)** |
| `acceleration_curve_power` | 1.3 | 1.0-2.0 | Throttle response curve (↓ = more linear acceleration) |
| `brake_power` | 2.0 | 1.0-3.0 | Braking force response (↑ = sharper braking) |

### Handling & Drift

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `steering_throttle_reduction` | 0.5 | 0.0-1.0 | **Throttle reduction while steering** (↑ = more drift effect) |
| `min_linear_scale` | 0.3 | 0.0-1.0 | Minimum speed during tight turns (↓ = easier tight turns) |
| `smoothing_factor` | 0.7 | 0.0-1.0 | Command smoothing (↓ = smoother/delayed, ↑ = more responsive) |

## Recommended Tuning Presets

### 🏎️ **Ultra Responsive** (Maximum arcade feel)
```yaml
steering_sensitivity: 1.5
steering_power: 1.3
deadzone: 0.05
trigger_deadzone: 0.01
max_linear_velocity: 3.0
max_angular_velocity: 5.5
steering_throttle_reduction: 0.6
smoothing_factor: 0.9
```

### 🚙 **Balanced (Default)** (Good all-around)
Current default settings are already optimized for this.

### 🛞️ **Slow & Precise** (Easier control)
```yaml
steering_sensitivity: 0.9
steering_power: 2.0
deadzone: 0.15
trigger_deadzone: 0.05
max_linear_velocity: 1.8
max_angular_velocity: 3.5
steering_throttle_reduction: 0.3
smoothing_factor: 0.5
```

## How to Adjust Parameters

### Method 1: Runtime Parameter Adjustment (Recommended for Testing)
```bash
# In another terminal, set parameters while the node is running:
ros2 param set /ps4_drive_node steering_sensitivity 1.5
ros2 param set /ps4_drive_node max_linear_velocity 3.0
ros2 param set /ps4_drive_node deadzone 0.05
```

### Method 2: Configuration File (Permanent)
Edit the parameters in your launch file or create a parameters YAML file:
```yaml
ps4_drive_node:
  ros__parameters:
    steering_sensitivity: 1.5
    max_linear_velocity: 3.0
    deadzone: 0.05
```

## Tuning Tips

### Issue: Rover drifts without input
**Solutions:**
- Reduce `deadzone` (currently 0.1)
- Reduce `steering_sensitivity` if it's too high
- Check your PS4 controller analog stick for wear

### Issue: Steering is too sensitive / twitchy
**Solutions:**
- Increase `deadzone` (try 0.15-0.2)
- Reduce `steering_sensitivity` (try 0.8-1.0)
- Increase `smoothing_factor` (try 0.8-0.95)

### Issue: Rover doesn't turn sharp enough
**Solutions:**
- Increase `steering_sensitivity` (try 1.5-1.8)
- Increase `max_angular_velocity` (try 5.0-6.0)
- Reduce `steering_power` (try 1.2-1.3 for more linear response)

### Issue: Acceleration feels slow
**Solutions:**
- Increase `max_linear_velocity` (try 2.8-3.5)
- Reduce `acceleration_curve_power` (try 1.1-1.2 for more linear)
- Reduce `trigger_deadzone` (try 0.01)

### Issue: Braking doesn't feel responsive
**Solutions:**
- Increase `brake_power` (try 2.5-3.0)
- Reduce `trigger_deadzone` (try 0.01-0.02)

### Issue: Turning feels sluggish at high speed
**Solutions:**
- Reduce `steering_throttle_reduction` (try 0.3-0.4)
- Increase `min_linear_scale` (try 0.5-0.7)

## Advanced: Understanding the Control Flow

1. **Raw Input** → PS4 analog stick/trigger values (-1.0 to 1.0)
2. **Deadzone** → Remove center drift and noise
3. **Normalization** → Convert triggers from [-1,1] to [0,1]
4. **Exponential Curve** → Apply non-linear response for better feel
5. **Sensitivity Multiplier** → Scale final output
6. **Smoothing** → Exponential moving average for arcade feel
7. **Output** → ROS2 Twist commands to diff_drive_controller

## Testing Changes

After changing parameters, observe:
- ✅ How responsive is the steering?
- ✅ Does the rover feel "arcade-like" or "realistic"?
- ✅ Can you make smooth turns at speed?
- ✅ Does acceleration feel natural?
- ✅ Can you make tight turns at low speed?

## Performance Notes

- **Update Rate**: Controller sampled at 50Hz
- **Command Timeout**: 0.5 seconds (rover stops if no commands)
- **Max Speed**: Limited by diff_drive_controller (2.5 m/s linear, 6.5 rad/s angular)

## Console Debugging

Enable DEBUG logging to see real-time values:
```bash
ros2 run ps4_drive_node ps4_drive_node --ros-args --log-level DEBUG
```

This will show: `CMD: linear.x=X.XX m/s, angular.z=X.XX rad/s`

---

**Happy driving! 🚀**
