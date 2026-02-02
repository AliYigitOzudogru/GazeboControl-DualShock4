#!/usr/bin/env python3
"""
PS4 Kumanda ile Rover Simülasyonu Ana Launch Dosyası

Bu launch dosyası tüm simülasyon bileşenlerini başlatır:
1. Gazebo Sim ile özel dünya
2. Robot durum yayıncısı
3. Rover URDF'ini sahneye ekle
4. ros2_control kontrolcüleri (joint_state_broadcaster, diff_drive_controller)
5. PS4 kumanda için joy düğümü
6. Özel PS4 sürüş düğümü
7. Gerekli topicler için ROS-Gazebo köprüsü

Yazar: Bilgisayar Mühendisliği Öğrencisi
Lisans: Apache 2.0
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
    Rover simülasyonu için launch açıklamasını oluştur.
    """
    
    # Paket dizinlerini al
    pkg_name = 'rover_sim'
    pkg_share = get_package_share_directory(pkg_name)
    
    # pkg_share'ın üst dizini - Gazebo'nun model://rover_sim/meshes/ bulması için gerekli
    pkg_share_parent = os.path.dirname(pkg_share)
    
    # Gazebo model yolunu ayarla - MESH YÜKLEME İÇİN ÖNEMLİ
    # Gazebo model://rover_sim/meshes/... aradığı için üst dizine ihtiyacımız var
    gazebo_model_path = SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=pkg_share_parent + ':' + pkg_share
    )
    
    # Uyumluluk için IGN_GAZEBO_RESOURCE_PATH değişkenini de ayarla
    ign_gazebo_resource_path = SetEnvironmentVariable(
        name='IGN_GAZEBO_RESOURCE_PATH',
        value=pkg_share_parent + ':' + pkg_share
    )
    
    # Önemli dosyalara giden yollar
    urdf_file = os.path.join(pkg_share, 'urdf', 'rover.urdf.xacro')
    world_file = os.path.join(pkg_share, 'worlds', 'rover_world.sdf')
    controllers_file = os.path.join(pkg_share, 'config', 'controllers.yaml')
    
    # Launch yapılandırma değişkenleri
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    world_arg = LaunchConfiguration('world', default=world_file)
    
    # Launch argümanlarını tanımla
    declare_use_sim_time_cmd = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='True ise simülasyon (Gazebo) saatini kullan'
    )
    
    declare_world_cmd = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Yüklenecek dünya dosyasının tam yolu'
    )
    
    # URDF/xacro dosyasını işle
    robot_description_config = xacro.process_file(urdf_file)
    robot_description = {'robot_description': robot_description_config.toxml()}
    
    # Robot Durum Yayıncısı Düğümü
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[
            robot_description,
            {'use_sim_time': use_sim_time}
        ]
    )
    
    # Gazebo Sim Başlat
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
    
    # Rover'ı Gazebo'da oluştur
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
    
    # Joint State Broadcaster Başlatıcı
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Diff Drive Controller Başlatıcı
    diff_drive_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Arm Controller Başlatıcı
    arm_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
        output='screen'
    )
    
    # Kontrolcü başlatıcılarını robot oluşturulduktan sonra çalıştır
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
    
    # Gerekli topicler için ROS-Gazebo Köprüsü
    # Clock köprüsü
    bridge_clock = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )
    
    # Odometry köprüsü (isteğe bağlı, gerekirse)
    bridge_odom = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/model/rover/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry'],
        output='screen',
        remappings=[
            ('/model/rover/odometry', '/odom_gazebo')
        ]
    )
    
    # Joy Düğümü (PS4 Kumanda Sürücüsü)
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'device_id': 1,  # PS4 Kablosuz Kumanda /dev/input/js1 üzerinde (device_id 1)
            'deadzone': 0.05,
            'autorepeat_rate': 20.0,
        }],
        output='screen'
    )
    
    # Özel PS4 Sürüş Düğümü
    ps4_drive_node = Node(
        package=pkg_name,
        executable='ps4_drive_node.py',
        name='ps4_drive_node',
        output='screen',
        parameters=[{
            'use_sim_time': use_sim_time,
            'max_linear_velocity': 2.0,
            'max_angular_velocity': 10.0,
            'deadman_button': 0,  # X butonu
            'enable_deadman': True,
            'steering_axis': 0,  # Sol çubuk yatay
            'accelerator_axis': 5,  # R2 tetik
            'brake_axis': 4,  # L2 tetik
            'deadzone': 0.03,
            'trigger_deadzone': 0.05,
            'exponential_steering': True,
            'steering_power': 1.3,
            'steering_sensitivity': 3.0,
            'invert_steering': False,
            'steering_throttle_reduction': 0.2,
            'min_linear_scale': 0.7,
            'smoothing_enabled': True,
            'smoothing_factor': 0.85,
        }]
    )
    
    # Launch açıklamasını oluştur
    ld = LaunchDescription()
    
    # Önce çevre değişkenlerini ekle
    ld.add_action(gazebo_model_path)
    ld.add_action(ign_gazebo_resource_path)
    
    # Launch argümanlarını ekle
    ld.add_action(declare_use_sim_time_cmd)
    ld.add_action(declare_world_cmd)
    
    # Düğümleri sırayla ekle
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
