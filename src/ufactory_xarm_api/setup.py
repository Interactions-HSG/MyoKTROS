from setuptools import setup

package_name = 'ufactory_xarm_api'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Iori Mizutani',
    maintainer_email='iomz@sazanka.io',
    description='xarm_api with rclpy',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'set_position = ufactory_xarm_api.set_position:main',
            'set_servo_angle = ufactory_xarm_api.set_servo_angle:main',
        ],
    },
)
