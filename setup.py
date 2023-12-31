import os
from glob import glob
from setuptools import setup

package_name = 'roskafka'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*'))
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alexander Grueneberg',
    maintainer_email='ros@agrueneberg.info',
    description='ROS Kafka Bridge',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'ros_kafka = roskafka.ros_kafka:main',
            'kafka_ros = roskafka.kafka_ros:main',
        ],
    },
)
