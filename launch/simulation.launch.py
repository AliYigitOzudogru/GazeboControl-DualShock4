#!/usr/bin/env python3
"""
Master Launch File for Rover Simulation with PS4 Controller

This launch file brings up the complete simulation stack:
1. Gazebo Sim with custom world
2. Robot state publisher
3. Spawn rover URDF
4. ros2_control controllers (joint_state_broadcaster, diff_drive_controller)
5. Joy node for PS4 controller
6. Custom PS4 drive node
7. ROS-Gazebo bridge for essential topics

Author: ROS 2 Gazebo Simulation Team
License: Apache 2.0
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, SetEnvironmentVariable
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
import xacro


def generate_launch_description():
    """
    Generate the launch description for the complete rover simulation.
    """
    
    # Get package directories
    pkg_name = 'rover_sim'
    pkg_share = get_package_share_directory(pkg_name)
    
    # Parent directory of pkg_share - needed for Gazebo to find model://rover_sim/meshes/
    pkg_share_parent = os.path.dirname(pkg_share)
    
    # Set Gazebo model path - THIS IS CRITICAL FOR MESH LOADING
    # Gazebo looks for model://rover_sim/meshes/... so we need the parent directory
    gazebo_model_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=pkg_share_parent + ':' + pkg_share
    )
    
    # Also set IGN_GAZEBO_RESOURCE_PATH for compatibility
    ign_gazebo_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=pkg_share_parent + ':' + pkg_share
    )
    
    # Paths to important files
    urdf_file = os.path.join(pkg_share, 'urdf', 'rover.urdf.xacro')
    world_file = os.path.join(pkg_share, 'worlds', 'rover_world.sdf')
    controllers_file = os.path.join(pkg_share, 'config', 'controllers.yaml')
    
    # Launch configuration variables
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_arg = LaunchConfiguration('world', default=world_file)
    
    # Declare launch arguments
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    )
    
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Full path to world file to load'
    )
    
    # Process the URDF/xacro file
    robot_description_config = xacro.process_file(urdf_file)
    robot_description = {'robot_description': robot_description_config.toxml()}
    
    # Robot State Publisher Node
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
        ]
    )
    
    # Gazebo Sim Launch
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            ])
        ]),
        launch_arguments={
            'gz_args': ['-r -v4 ', world_arg],
            'on_exit_shutdown': 'true'
        }.items()
    )
    
    # Spawn the rover in Gazebo
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'rover',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '1.0',
            '-Y', '0.0'
        ],
        output='screen'
    )
    
    # Joint State Broadcaster Spawner
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Diff Drive Controller Spawner
    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Arm Controller Spawner
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Delay controller spawners until robot is spawned
    delay_joint_state_broadcaster = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=spawn_robot,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )
    
    delay_diff_drive_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[diff_drive_controller_spawner],
        )
    )
    
    delay_arm_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=diff_drive_controller_spawner,
            on_exit=[arm_controller_spawner],
        )
    )
    
    # ROS-Gazebo Bridge for essential topics
    # Bridge clock
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )
    
    # Bridge odometry (optional, if needed)
    bridge_odom = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/model/rover/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
        output='screen',
        remappings=[
            ('/model/rover/odometry', '/odom_gazebo')
        ]
    )
    
    # Joy Node (PS4 Controller Driver)
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'device_id': 1,  # Use js1 for PS4 controller
            'deadzone': 0.05,
            'autorepeat_rate': 20.0,
        }],
        output='screen'
    )
    
    # Custom PS4 Drive Node
    ps4_drive_node = Node(
        package=pkg_name,
        executable='ps4_drive_node.py',
        name='ps4_drive_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'max_linear_velocity': 2.0,
            'max_angular_velocity': 3.0,
            'deadman_button': 0,  # X button
            'enable_deadman': True,
            'steering_axis': 0,  # Left stick horizontal
            'accelerator_axis': 5,  # R2 trigger
            'brake_axis': 4,  # L2 trigger
            'deadzone': 0.1,
            'trigger_deadzone': 0.05,
            'exponential_steering': True,
            'steering_sensitivity': 1.0,
        }]
    )
    
    # Create the launch description
    ld = LaunchDescription()
    
    # Add environment variables FIRST
    ld.add_action(gazebo_model_path)
    ld.add_action(ign_gazebo_resource_path)
    
    # Add launch arguments
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_world_cmd)
    
    # Add nodes in order
    ld.add_action(gazebo)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(spawn_robot)
    ld.add_action(delay_joint_state_broadcaster)
    ld.add_action(delay_diff_drive_controller)
    ld.add_action(delay_arm_controller)
    ld.add_action(bridge_clock)
    ld.add_action(bridge_odom)
    ld.add_action(joy_node)
    ld.add_action(ps4_drive_node)
    
    return ld
