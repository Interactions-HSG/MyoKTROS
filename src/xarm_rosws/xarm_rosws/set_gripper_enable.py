import rclpy
from rclpy.node import Node
from xarm_msgs.srv import SetInt16


class SetGripperEnableClient(Node):
    def __init__(self):
        super().__init__('set_gripper_enable_client_async')
        self.c = self.create_client(SetInt16, '/ufactory/set_gripper_enable')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = SetInt16.Request()

    def send_request(self, data: int):
        self.req.data = data
        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
