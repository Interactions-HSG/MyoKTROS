import rclpy
from rclpy.node import Node
from xarm_msgs.srv import MoveJoint


class SetServoAngleClient(Node):
    def __init__(self):
        super().__init__('set_servo_angle_client_async')
        self.c = self.create_client(MoveJoint, '/ufactory/set_servo_angle')
        while not self.c.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('service not available, waiting again...')
        self.req = MoveJoint.Request()

    def send_request(self, angles, speed: float, acc: float, mvtime: float):
        self.req.angles = angles
        self.req.speed = speed
        self.req.acc = acc
        self.req.mvtime = mvtime

        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()
