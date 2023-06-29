import rclpy
from rclpy.node import Node
from xarm_msgs.srv import Call


class OpenLite6GripperClient(Node):
    def __init__(self):
        super().__init__('open_lite6_gripper_client_async')
        self.c = self.create_client(Call, '/ufactory/open_lite6_gripper')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = Call.Request()

    def send_request(self):
        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
