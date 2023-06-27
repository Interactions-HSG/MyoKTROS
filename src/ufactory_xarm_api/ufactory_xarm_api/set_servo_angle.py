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

    def send_request(self):
        self.req.angles = [-0.58, 0.0, 0.0, 0.0, 0.0, 0.0]
        self.req.speed = 0.35
        self.req.acc = 10.0
        self.req.mvtime = 0.0

        self.future = self.c.call_async(self.req)
        rclpy.spin_until_future_complete(self, self.future)
        return self.future.result()


def main():
    rclpy.init()

    sic = SetServoAngleClient()
    response = sic.send_request()
    sic.get_logger().info(f"/ufactory/set_servo_angle: {response}")

    sic.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
