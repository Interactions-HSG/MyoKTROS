import rclpy
from rclpy.node import Node
from xarm_msgs.srv import MoveHome


class MoveGohomeClient(Node):
    def __init__(self):
        super().__init__('move_gohome_client_async')
        self.c = self.create_client(MoveHome, '/ufactory/move_gohome')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = MoveHome.Request()

    def send_request(self, speed: float, acc: float, mvtime: float):
        self.req.speed = speed
        self.req.acc = acc
        self.req.mvtime = mvtime

        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
