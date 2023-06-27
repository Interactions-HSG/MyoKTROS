import rclpy
from rclpy.node import Node
from xarm_msgs.srv import MoveCartesian


class SetPositionClient(Node):
    def __init__(self):
        super().__init__('set_position_client_async')
        self.c = self.create_client(MoveCartesian, '/ufactory/set_position')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = MoveCartesian.Request()

    def send_request(self, pose, speed: float, acc: float, mvtime: float):
        self.req.pose = pose
        self.req.speed = speed
        self.req.acc = acc
        self.req.mvtime = mvtime

        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
