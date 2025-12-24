import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    pkg_name = 'my_robot'
    pkg_share = get_package_share_directory(pkg_name)

    # 1. 修正路径：包含系统模型路径，否则找不到地面(ground_plane)和太阳(sun)
    # 同时强制使用 X11 渲染，防止虚拟机崩溃
    gazebo_model_path = '/usr/share/gazebo-11/models:' + os.path.join(pkg_share, 'models')
    if 'GAZEBO_MODEL_PATH' in os.environ:
        gazebo_model_path += os.pathsep + os.environ['GAZEBO_MODEL_PATH']

    set_gazebo_path = SetEnvironmentVariable(
        name='GAZEBO_MODEL_PATH',
        value=gazebo_model_path
    )
    
    # 强制 QT 使用 xcb，防止在 Wayland/虚拟机下闪退
    set_qt_platform = SetEnvironmentVariable(name='QT_QPA_PLATFORM', value='xcb')

    # 机器人 URDF
    xacro_file = os.path.join(pkg_share, 'urdf', 'myrobot.xacro')
    robot_description_raw = xacro.process_file(xacro_file).toxml()

    # Gazebo 基础启动 - 确保加载 maze.world
    world_path = os.path.join(pkg_share, 'worlds', 'maze.world')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': world_path}.items()
    )

    # 发布机器人状态
    node_robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_raw, 'use_sim_time': True}]
    )

    # 生成机器人 - 增加超时时间防止加载大型迷宫时超时
    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-topic', 'robot_description', 
                   '-entity', 'my_robot', 
                   '-z', '0.5',
                   '-timeout', '30'],
        output='screen'
    )

    return LaunchDescription([
        set_gazebo_path,
        set_qt_platform,
        gazebo,
        node_robot_state_publisher,
        TimerAction(period=8.0, actions=[spawn_entity]), # 迷宫大，稍微多等一会儿
    ])
