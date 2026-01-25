#!/usr/bin/env python3
"""
PS4 Racing-Style Controller Node for ROS 2 Rover Control

This node subscribes to /joy messages from a PS4 DualShock controller
and publishes velocity commands to the diff_drive_controller.

Control Scheme (Racing Style):
- R2 Trigger (Axis 5): Accelerator (Forward)
- L2 Trigger (Axis 4): Brake/Reverse
- Left Analog Stick Horizontal (Axis 0): Steering
- X Button (Button 0): Deadman switch (must be held to enable driving)

Author: ROS 2 Gazebo Simulation Team
License: Apache 2.0
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Joy
from geometry_msgs.msg import Twist
import math


class PS4DriveNode(Node):
    """
    Custom PS4 controller driver for racing-style rover control.
    Implements trigger-based acceleration and analog steering.
    """

    def __init__(self):
        super().__init__('ps4_drive_node')
        
        # Declare parameters with defaults
        self.declare_parameter('max_linear_velocity', 2.0)  # m/s
        self.declare_parameter('max_angular_velocity', 3.0)  # rad/s
        self.declare_parameter('deadman_button', 0)  # X button
        self.declare_parameter('enable_deadman', True)  # Enable/disable deadman switch
        self.declare_parameter('steering_axis', 0)  # Left stick horizontal
        self.declare_parameter('accelerator_axis', 5)  # R2 trigger
        self.declare_parameter('brake_axis', 4)  # L2 trigger
        self.declare_parameter('deadzone', 0.25)  # Joystick deadzone (increased to prevent drift)
        self.declare_parameter('trigger_deadzone', 0.05)  # Trigger deadzone
        self.declare_parameter('exponential_steering', True)  # Apply exponential curve to steering
        self.declare_parameter('steering_sensitivity', 1.0)  # Steering multiplier
        
        # Get parameters
        self.max_linear_vel = self.get_parameter('max_linear_velocity').value
        self.max_angular_vel = self.get_parameter('max_angular_velocity').value
        self.deadman_button = self.get_parameter('deadman_button').value
        self.enable_deadman = self.get_parameter('enable_deadman').value
        self.steering_axis = self.get_parameter('steering_axis').value
        self.accelerator_axis = self.get_parameter('accelerator_axis').value
        self.brake_axis = self.get_parameter('brake_axis').value
        self.deadzone = self.get_parameter('deadzone').value
        self.trigger_deadzone = self.get_parameter('trigger_deadzone').value
        self.exponential_steering = self.get_parameter('exponential_steering').value
        self.steering_sensitivity = self.get_parameter('steering_sensitivity').value
        
        # Create subscriber to joy topic
        self.joy_sub = self.create_subscription(
            Joy,
            '/joy',
            self.joy_callback,
            10
        )
        
        # Create publisher for velocity commands (unstamped for diff_drive_controller)
        self.cmd_vel_pub = self.create_publisher(
            Twist,
            '/diff_drive_controller/cmd_vel_unstamped',
            10
        )
        
        # Initialize last command time for timeout detection
        self.last_joy_time = self.get_clock().now()
        
        # Create a timer for watchdog (stops rover if no joy messages)
        self.watchdog_timer = self.create_timer(0.1, self.watchdog_callback)
        self.watchdog_timeout = 1.0  # seconds
        
        self.get_logger().info('PS4 Racing Controller Node Started')
        self.get_logger().info(f'Max Linear Velocity: {self.max_linear_vel} m/s')
        self.get_logger().info(f'Max Angular Velocity: {self.max_angular_vel} rad/s')
        self.get_logger().info(f'Deadman Switch: {"Enabled" if self.enable_deadman else "Disabled"} (Button {self.deadman_button})')
        self.get_logger().info('Controls: R2=Accelerate, L2=Brake/Reverse, Left Stick=Steer')

    def apply_deadzone(self, value, deadzone):
        """
        Apply deadzone to joystick/trigger values.
        Values within deadzone return 0.0.
        """
        if abs(value) < deadzone:
            return 0.0
        # Scale the remaining range to maintain smooth control
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - deadzone) / (1.0 - deadzone)

    def normalize_trigger(self, trigger_value):
        """
        Normalize PS4 trigger value from [-1.0, 1.0] to [0.0, 1.0].
        PS4 triggers typically read -1.0 when released and 1.0 when fully pressed.
        """
        # Convert from [-1, 1] to [0, 1]
        normalized = (trigger_value + 1.0) / 2.0
        return max(0.0, min(1.0, normalized))  # Clamp to [0, 1]

    def apply_exponential_curve(self, value, power=2.0):
        """
        Apply exponential curve for more precise control at low speeds.
        Maintains sign of input.
        """
        sign = 1.0 if value >= 0 else -1.0
        return sign * (abs(value) ** power)

    def joy_callback(self, msg: Joy):
        """
        Process joystick input and publish velocity commands.
        Implements racing-style controls with triggers and analog steering.
        """
        # Update last message time
        self.last_joy_time = self.get_clock().now()
        
        # Check deadman switch if enabled
        if self.enable_deadman:
            if len(msg.buttons) <= self.deadman_button or msg.buttons[self.deadman_button] == 0:
                # Deadman not pressed, stop the rover
                self.publish_stop_command()
                return
        
        # Initialize twist message
        twist = Twist()
        
        # Get and normalize trigger values
        # Note: Default PS4 mapping has triggers on axes 4 (L2) and 5 (R2)
        # Check if axes exist (different joy drivers may have different mappings)
        if len(msg.axes) > max(self.accelerator_axis, self.brake_axis):
            # Get raw trigger values
            accelerator_raw = msg.axes[self.accelerator_axis]
            brake_raw = msg.axes[self.brake_axis]
            
            # Normalize triggers from [-1, 1] to [0, 1]
            accelerator = self.normalize_trigger(accelerator_raw)
            brake = self.normalize_trigger(brake_raw)
            
            # Apply trigger deadzone
            accelerator = self.apply_deadzone(accelerator, self.trigger_deadzone)
            brake = self.apply_deadzone(brake, self.trigger_deadzone)
            
            # Calculate linear velocity (forward - backward)
            # R2 (accelerator) = positive (forward)
            # L2 (brake) = negative (backward)
            linear_x = (accelerator - brake) * self.max_linear_vel
            
            twist.linear.x = linear_x
        else:
            self.get_logger().warn('Trigger axes not available, check joy driver configuration')
        
        # Get steering input from left analog stick (horizontal)
        if len(msg.axes) > self.steering_axis:
            steering_raw = msg.axes[self.steering_axis]
            
            # Apply deadzone
            steering = self.apply_deadzone(steering_raw, self.deadzone)
            
            # Apply exponential curve if enabled (for finer control)
            if self.exponential_steering and steering != 0.0:
                steering = self.apply_exponential_curve(steering, power=2.0)
            
            # Apply sensitivity multiplier
            steering *= self.steering_sensitivity
            
            # Calculate angular velocity (left stick controls turning)
            # Positive left stick = turn left (positive angular.z in ROS convention)
            angular_z = steering * self.max_angular_vel
            
            twist.angular.z = angular_z
        else:
            self.get_logger().warn('Steering axis not available')
        
        # Publish the velocity command
        self.cmd_vel_pub.publish(twist)
        
        # Log current command (throttled to avoid spam)
        if abs(twist.linear.x) > 0.01 or abs(twist.angular.z) > 0.01:
            self.get_logger().debug(
                f'CMD: linear.x={twist.linear.x:.2f} m/s, angular.z={twist.angular.z:.2f} rad/s'
            )

    def publish_stop_command(self):
        """
        Publish a zero velocity command to stop the rover.
        """
        twist = Twist()
        twist.linear.x = 0.0
        twist.linear.y = 0.0
        twist.linear.z = 0.0
        twist.angular.x = 0.0
        twist.angular.y = 0.0
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)

    def watchdog_callback(self):
        """
        Watchdog timer to stop rover if no joystick messages received.
        Safety feature to prevent runaway robot.
        """
        time_since_last_joy = (self.get_clock().now() - self.last_joy_time).nanoseconds / 1e9
        
        if time_since_last_joy > self.watchdog_timeout:
            # No joy messages for too long, ensure rover is stopped
            self.publish_stop_command()
            # Only log once per timeout period
            if time_since_last_joy < self.watchdog_timeout + 0.2:
                self.get_logger().warn('Joystick timeout - stopping rover')


def main(args=None):
    """
    Main entry point for the PS4 drive node.
    """
    rclpy.init(args=args)
    
    try:
        node = PS4DriveNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error in PS4 drive node: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
