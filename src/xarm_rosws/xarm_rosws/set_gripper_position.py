import rclpy
from rclpy.node import Node
from xarm_msgs.srv import GripperMove


class SetGripperPositionClient(Node):
    def __init__(self):
        super().__init__('set_gripper_position_client_async')
        self.c = self.create_client(GripperMove, '/ufactory/set_gripper_position')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = GripperMove.Request()

    def send_request(self, pos: float, wait: bool = False, timeout: float = 10):
        self.req.pos = pos
        self.req.wait = wait
        self.req.timeout = timeout
        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
