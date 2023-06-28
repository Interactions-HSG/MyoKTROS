from setuptools import setup

package_name = 'xarm_rosws'

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
    description='xarm_rosws: ros2 xarm_api via websocket',
    license='MIT',
    entry_points={
        'console_scripts': [
            'run = xarm_rosws.server:run',
        ],
    },
)
