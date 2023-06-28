import rclpy
from rclpy.node import Node
from xarm_msgs.srv import GetFloat32List


class GetServoAngleClient(Node):
    def __init__(self):
        super().__init__('get_servo_angle_client_async')
        self.c = self.create_client(GetFloat32List, '/ufactory/get_servo_angle')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = GetFloat32List.Request()

    def send_request(self):
        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
